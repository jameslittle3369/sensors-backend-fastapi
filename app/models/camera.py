from sqlmodel import Field, SQLModel


class Camera(SQLModel, table=True):
    __tablename__ = "cameras_camera"

    id: int | None = Field(default=None, primary_key=True)
    name: str | None = Field(max_length=100, default=None)
    # Plain storage key/path string -- Django's ImageField/S3 storage
    # abstraction is not rebuilt here. Actual image upload/serving is an
    # explicit follow-up decision, not guessed at in this migration.
    current_picture: str | None = Field(default=None)
