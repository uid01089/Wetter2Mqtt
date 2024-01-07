import xmltodict
import urllib.request
from zipfile import ZipFile
from io import BytesIO
from datetime import datetime
from PythonLib.DateUtil import DateTimeUtilities


class MosMix:
    def __init__(self, station: str) -> None:
        self.url = f"https://opendata.dwd.de/weather/local_forecasts/mos/MOSMIX_L/single_stations/{station}/kml/MOSMIX_L_LATEST_{station}.kmz"
        self.dataTable = {}
        self.timeTable = []

    def read(self) -> None:
        response = urllib.request.urlopen(self.url)
        zipData = response.read()

        with ZipFile(BytesIO(zipData), 'r') as zip_file:
            fileName = zip_file.namelist()[0]
            fileContent = zip_file.read(fileName)
            xmlDict = xmltodict.parse(fileContent)

            self.timeTable = xmlDict['kml:kml']['kml:Document']['kml:ExtendedData']['dwd:ProductDefinition']['dwd:ForecastTimeSteps']['dwd:TimeStep']

            for forecast in xmlDict['kml:kml']['kml:Document']['kml:Placemark']['kml:ExtendedData']['dwd:Forecast']:
                self.dataTable[forecast['@dwd:elementName']] = forecast['dwd:value'].split()

    def getValues(self, identifier: str) -> list[tuple]:

        result = None

        now = datetime.now()

        if identifier in self.dataTable:
            result = []

            for i in range(0, len(self.dataTable[identifier])):

                dateObject = DateTimeUtilities.parseIsoStr(self.timeTable[i])

                if dateObject >= now:
                    result.append((dateObject, self.dataTable[identifier][i]))

        return result
