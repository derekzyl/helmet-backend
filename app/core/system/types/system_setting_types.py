from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, StringConstraints

SettingKeyStr = Annotated[str, StringConstraints(max_length=100)]
SettingTypeStr = Annotated[str, StringConstraints(max_length=50)]
DescriptionStr = Annotated[str, StringConstraints(max_length=500)]


class SystemSettingBase(BaseModel):
    setting_key: SettingKeyStr
    setting_value: Optional[str] = None
    setting_type: SettingTypeStr
    description: Optional[DescriptionStr] = None
    is_system_wide: Optional[bool] = True
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
