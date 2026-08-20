"""
Ported near-verbatim from apps/api/v1/tstats/views.py::TstatsViewSet in the
Django reference app (create() + get_aq_sensor()). This is a device-scrape
job wearing an HTTP POST endpoint's clothes, not real client-facing CRUD --
kept behavior-identical per the "port as-is" scope decision, including its
rough edges (bare except/pass on the OWServer request, an unhandled
Thermometer.DoesNotExist-equivalent if a scraped romid isn't registered,
and no guard around the Dyson MQTT connection timing out).
"""

import json
import syslog
import time
import xml.etree.ElementTree as ET

import paho.mqtt.client as mqtt
import requests
from libpurecool.dyson_device import NetworkDevice
from libpurecool.dyson_pure_hotcool_link import DysonPureHotCoolLink
from sqlmodel import Session


import logging

from app.core.config import get_settings
from app.models.aqsensor import AQLog, AQSensor
from app.models.tstat import Thermometer, TstatLog

_OWSERVER_NS = "{http://www.embeddeddatasystems.com/schema/owserver}owd_DS18B20"
logger = logging.getLogger("uvicorn.error")

def scrape_owserver(session: Session) -> list[str] | None:
    settings = get_settings()
    logger.info("This is an info log inside an endpoint")
    logger.info("OWServer:  %s", settings.owserver_url)

    try:
        api_response = requests.get(settings.owserver_url)
    except Exception:
        return None
    logger.info("Past the tstat get")
    api_response.encoding = "UTF-8"
    xml_tree = ET.fromstring(api_response.text)

    msg: list[str] = []
    for tstat_el in xml_tree.iter(_OWSERVER_NS):
        romid = ""
        value = ""
        for val in tstat_el:
            if "ROMId" in str(val):
                syslog.syslog(f"ROMId:  {val.text}")
                msg.append(val.text)
                romid = val.text
            if "Temperature" in str(val):
                syslog.syslog(f"Temperature:  {val.text}")
                msg.append(val.text)
                value = val.text
        # Unhandled if romid isn't a registered Thermometer, matching
        # Django's Thermometer.objects.get(romid=romid) -- no try/except
        # was added there either.
        thermometer = session.get(Thermometer, romid)
        logger.info("Got the thermometer")
        if thermometer is not None:
            session.add(TstatLog(romid_id=thermometer.romid, primary_value=value))
            session.commit()

    return msg


def scrape_dyson(session: Session) -> None:
    settings = get_settings()
    device_info = {
        "Serial": settings.dyson_serial,
        "Name": settings.dyson_name,
        "Version": settings.dyson_version,
        "LocalCredentials": settings.dyson_credentials,
        "AutoUpdate": True,
        "NewVersionAvailable": False,
        "ProductType": settings.dyson_product_type,
        "ConnectionType": "wss",
    }
    logger.info("Dyson Serial:  %s", settings.dyson_serial)
    device = DysonPureHotCoolLink(device_info)
    device._network_device = NetworkDevice(device._name, settings.dyson_host, "1883")
    device._mqtt = mqtt.Client(userdata=device)
    device._mqtt.on_message = device.on_message
    device._mqtt.on_connect = device.on_connect
    device._mqtt.username_pw_set(device._serial, device._credentials)
    device._mqtt.connect(device._network_device.address, int(device._network_device.port))
    device._mqtt.loop_start()

    try:
        # Matches Django: unhandled if this queue.get() times out (no
        # try/except around it there either).
        connected = device._connection_queue.get(timeout=10)
        if connected:
            payload = {
                "msg": "REQUEST-PRODUCT-ENVIRONMENT-CURRENT-SENSOR-DATA",
                "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            try:
                device._mqtt.publish(
                    f"{device._product_type}/{device._serial}/command", json.dumps(payload)
                )
                time.sleep(5)
            except Exception:
                syslog.syslog("ndevices publish exception")

            try:
                time.sleep(5)
                aq_sensor = session.get(AQSensor, 1)

                env = device.environmental_state
                # Measurement values ARE what Django actually wrote, not
                # the declared choice set (see AQLog.measurement comment)
                # -- P25R/P10R/HUMIDITY/TEMP, not PM25R/PM10R/HUM/Temp.
                session.add(AQLog(aq_sensor_id=aq_sensor.id, measurement="VOC", value=env.volatile_organic_compounds))
                session.add(AQLog(aq_sensor_id=aq_sensor.id, measurement="NO2", value=env.nitrogen_dioxide))
                session.add(AQLog(aq_sensor_id=aq_sensor.id, measurement="P25R", value=env.p25r))
                session.add(AQLog(aq_sensor_id=aq_sensor.id, measurement="P10R", value=env.p10r))
                session.add(AQLog(aq_sensor_id=aq_sensor.id, measurement="PM25", value=env.particulate_matter_25))
                session.add(AQLog(aq_sensor_id=aq_sensor.id, measurement="PM10", value=env.particulate_matter_10))
                session.add(AQLog(aq_sensor_id=aq_sensor.id, measurement="HUMIDITY", value=env.humidity))
                ftemp = (env.temperature - 273.15) * 9 / 5 + 32
                session.add(AQLog(aq_sensor_id=aq_sensor.id, measurement="TEMP", value=ftemp))
                session.commit()
            except Exception as e:
                syslog.syslog("ndevices environmental exception")
                print("ndevices environmental exception")
                print(e.__doc__)
    finally:
        device._mqtt.loop_stop()
        device._mqtt.disconnect()


def run_ingestion(session: Session) -> list[str] | None:
    msg = scrape_owserver(session)
    if msg is not None:
        scrape_dyson(session)
    return msg
