from devices.base import BaseDeviceDriver
from database.models import InstanceModel

class UGPhoneDriver(BaseDeviceDriver):
    def __init__(self, instance_config: InstanceModel):
        super().__init__(instance_config)

class VMOSDriver(BaseDeviceDriver):
    def __init__(self, instance_config: InstanceModel):
        super().__init__(instance_config)

class RedfingerDriver(BaseDeviceDriver):
    def __init__(self, instance_config: InstanceModel):
        super().__init__(instance_config)

class VSPhoneDriver(BaseDeviceDriver):
    def __init__(self, instance_config: InstanceModel):
        super().__init__(instance_config)
