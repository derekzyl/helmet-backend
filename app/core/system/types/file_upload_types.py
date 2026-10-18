from typing import Annotated, Optional
from pydantic import BaseModel, StringConstraints, ConfigDict, Field

# Type aliases for FileUpload
FilenameStr = Annotated[str, StringConstraints(max_length=255)]
FilePathStr = Annotated[str, StringConstraints(max_length=500)]
MimeTypeStr = Annotated[str, StringConstraints(max_length=100)]
FileTypeStr = Annotated[str, StringConstraints(max_length=50)]
EntityTypeStr = Annotated[str, StringConstraints(max_length=100)]
EntityIdStr = Annotated[str, StringConstraints(max_length=255)]

# Type aliases for SystemSetting
SettingKeyStr = Annotated[str, StringConstraints(max_length=100)]
SettingTypeStr = Annotated[str, StringConstraints(max_length=50)]
DescriptionStr = Annotated[str, StringConstraints(max_length=500)]


# FileUpload Schemas
class FileUploadBase(BaseModel):
    original_filename: FilenameStr
    stored_filename: FilenameStr
    file_path: FilePathStr
    file_size: Annotated[int, Field(ge=0, description="File size must be non-negative")]
    mime_type: Optional[MimeTypeStr] = None
    file_type: FileTypeStr
    entity_type: Optional[EntityTypeStr] = None
    entity_id: Optional[EntityIdStr] = None


class CreateFileUpload(FileUploadBase):
    uploaded_by_id: str


class UpdateFileUpload(BaseModel):
    original_filename: Optional[FilenameStr] = None
    stored_filename: Optional[FilenameStr] = None
    file_path: Optional[FilePathStr] = None
    file_size: Optional[Annotated[int, Field(ge=0, description="File size must be non-negative")]] = None
    mime_type: Optional[MimeTypeStr] = None
    file_type: Optional[FileTypeStr] = None
    entity_type: Optional[EntityTypeStr] = None
    entity_id: Optional[EntityIdStr] = None


class FileUploadOut(FileUploadBase):
    id: str
    uploaded_by_id: str
    
    model_config = ConfigDict(from_attributes=True)


# SystemSetting Schemas
class SystemSettingBase(BaseModel):
    setting_key: SettingKeyStr
    setting_value: Optional[str] = None
    setting_type: SettingTypeStr
    description: Optional[DescriptionStr] = None
    is_system_wide: Optional[bool] = False
    scope_id: Optional[str] = None


class CreateSystemSetting(SystemSettingBase):
    pass


class UpdateSystemSetting(BaseModel):
    setting_key: Optional[SettingKeyStr] = None
    setting_value: Optional[str] = None
    setting_type: Optional[SettingTypeStr] = None
    description: Optional[DescriptionStr] = None
    is_system_wide: Optional[bool] = None
    scope_id: Optional[str] = None


class SystemSettingOut(SystemSettingBase):
    id: str
    
    model_config = ConfigDict(from_attributes=True)