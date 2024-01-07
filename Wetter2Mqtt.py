from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from datetime import datetime
import paho.mqtt.client as pahoMqtt
from MosMix import MosMix


from PythonLib.DictUtil import DictUtil


from PythonLib.JsonUtil import JsonUtil
from PythonLib.Mqtt import Mqtt
from PythonLib.DateUtil import DateTimeUtilities
from PythonLib.MqttConfigContainer import MqttConfigContainer
from PythonLib.Scheduler import Scheduler
from PythonLib.Stream import Stream
from PythonLib.DateUtil import DateTimeUtilities


logger = logging.getLogger('Wetter2Mqtt')

DATA_PATH = Path(os.getenv('DATA_PATH', "."))


# https://github.com/earthobservations/wetterdienst/blob/main/examples/mosmix_forecasts.py
# https://wetterdienst.readthedocs.io/en/latest/data/coverage/dwd/mosmix/hourly.html

# https://opendata.dwd.de/weather/local_forecasts/mos/MOSMIX_L/single_stations/P366/kml/


class Module:
    def __init__(self) -> None:
        self.scheduler = Scheduler()
        self.mqttClient = Mqtt("koserver.iot", "/house/agents/Wetter2Mqtt", pahoMqtt.Client("Wetter2Mqtt"))
        self.config = MqttConfigContainer(self.mqttClient, "/house/agents/Wetter2Mqtt/config", DATA_PATH.joinpath("Wetter2Mqtt.json"), {})
        self.dwd = MosMix('P366')

    def getConfig(self) -> MqttConfigContainer:
        return self.config

    def getScheduler(self) -> Scheduler:
        return self.scheduler

    def getMqttClient(self) -> Mqtt:
        return self.mqttClient

    def setup(self) -> None:
        self.config.setup()
        self.scheduler.scheduleEach(self.mqttClient.loop, 500)
        self.scheduler.scheduleEach(self.config.loop, 60000)

    def getDwd(self) -> MosMix:
        return self.dwd

    def loop(self) -> None:
        self.scheduler.loop()


class Wetter2Mqtt:

    def __init__(self, module: Module) -> None:
        self.configContainer = module.getConfig()
        self.mqttClient = module.getMqttClient()
        self.scheduler = module.getScheduler()
        self.dwd = module.getDwd()
        self.config = {}

    def setup(self) -> None:

        self.configContainer.subscribeToConfigChange(self.__updateConfig)

        self.__getWeatherData()
        self.scheduler.scheduleEach(self.__getWeatherData, 30 * 60 * 1000)
        self.scheduler.scheduleEach(self.__keepAlive, 10000)

    def __updateConfig(self, config: dict) -> None:
        self.config = config

    def __getWeatherData(self) -> None:

        tree = {}

        # rad1h: 'rad1h'
        # n:     'cloud_cover_total'
        # ff:    'wind_speed'
        # ttt:   'temperature_air_mean_200'

        self.dwd.read()

        tree['temperature_air_mean_200'] = []
        for timeAndValue in self.dwd.getValues('TTT')[0:12]:
            timeStr = DateTimeUtilities.dateObj2IsoStr(timeAndValue[0])
            value = float(timeAndValue[1]) - 273.15
            tree['temperature_air_mean_200'].append({'time': timeStr, 'value': value})

        tree['cloud_cover_total'] = []
        for timeAndValue in self.dwd.getValues('N')[0:12]:
            timeStr = DateTimeUtilities.dateObj2IsoStr(timeAndValue[0])
            value = float(timeAndValue[1])
            tree['cloud_cover_total'].append({'time': timeStr, 'value': value})

        tree['wind_speed'] = []
        for timeAndValue in self.dwd.getValues('FF')[0:12]:
            timeStr = DateTimeUtilities.dateObj2IsoStr(timeAndValue[0])
            value = float(timeAndValue[1])
            tree['wind_speed'].append({'time': timeStr, 'value': value})

        tree['global_irradiance'] = []
        for timeAndValue in self.dwd.getValues('Rad1h')[0:12]:
            timeStr = DateTimeUtilities.dateObj2IsoStr(timeAndValue[0])
            value = float(timeAndValue[1])
            tree['global_irradiance'].append({'time': timeStr, 'value': value})

        tree['precipitation_height_significant_weather_last_1h'] = []
        for timeAndValue in self.dwd.getValues('RR1c')[0:12]:
            timeStr = DateTimeUtilities.dateObj2IsoStr(timeAndValue[0])
            value = float(timeAndValue[1])
            tree['precipitation_height_significant_weather_last_1h'].append({'time': timeStr, 'value': value})

        valuesForSending = DictUtil.flatDict(tree, "values")

        for value in valuesForSending:
            self.mqttClient.publishOnChange(value[0], value[1])

    def __keepAlive(self) -> None:
        self.mqttClient.publishIndependentTopic('/house/agents/Wetter2Mqtt/heartbeat', DateTimeUtilities.getCurrentDateString())
        self.mqttClient.publishIndependentTopic('/house/agents/Wetter2Mqtt/subscriptions', JsonUtil.obj2Json(self.mqttClient.getSubscriptionCatalog()))


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('Wetter2Mqtt').setLevel(logging.DEBUG)

    module = Module()
    module.setup()

    Wetter2Mqtt(module).setup()

    print("Wetter2Mqtt is running!")

    while (True):
        module.loop()
        time.sleep(0.25)


if __name__ == '__main__':
    main()
