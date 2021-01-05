# -*- coding: utf8 -*-
# Input the Libraries
# 라이브러리 설정
import requests
import json
import RPi.GPIO as GPIO
import datetime
import pytz
from time import sleep
from pyowm import OWM
import os
from bs4 import BeautifulSoup
import math

# Setup Pin Number
# 핀 설정
pirPin = 23
trigPin = 13
echoPin = 19

# Setup Pin Mode
# 핀 모드 설정
GPIO.setmode(GPIO.BCM)
GPIO.setup(pirPin, GPIO.IN)
GPIO.setup(trigPin, GPIO.OUT)
GPIO.setup(echoPin, GPIO.IN)

# Get Latitude and Longitude from IP Address using API
# IP 주소로 위도와 경도를 알아내기
recvd = requests.get('http://ip-api.com/json')
geo = json.loads(recvd.text)
print(geo)
print(geo['lat'])
print(geo['lon'])
print(geo['city'])
print(geo['regionName'])
print(geo['country'])

# Convert to Korea Meteorological Administration X, Y Coordinates from latitude and longitude
# 위도와 경도를 가지고 기상청 X, Y 좌표로 변환
RE = 6371.00877 # Earth Radius / 지구 반경 (km)
GRID = 5.0 # Lattice Spacing / 격자 간격 (km)
SLAT1 = 30.0 # Projection Latitude 1 / 투영 위도 1 (Degree)
SLAT2 = 60.0 # Projection Latitude 2 / 투영 위도 2 (Degree)
OLON = 126.0 # Reference Point Longitude / 기준점 경도 (Degree)
OLAT = 38.0 # Reference Point Latitude / 기준점 위도 (Degree)
XO = 43 # Reference Point X Coordinate / 기준점 X 좌표 (GRID)
YO = 136 # Reference Point Y Coordinate / 기준점 Y 좌표 (GRID)
DEGRAD = math.pi / 180.0
RADDEG = 180.0 / math.pi

re = RE / GRID
slat1 = SLAT1 * DEGRAD
slat2 = SLAT2 * DEGRAD
olon = OLON * DEGRAD
olat = OLAT * DEGRAD
sn = math.tan(math.pi * 0.25 + slat2 * 0.5) / math.tan(math.pi * 0.25 + slat1 * 0.5)
sn = math.log(math.cos(slat1) / math.cos(slat2)) / math.log(sn)
sf = math.tan(math.pi * 0.25 + slat1 * 0.5)
sf = math.pow(sf, sn) * math.cos(slat1) / sn
ro = math.tan(math.pi * 0.25 + olat * 0.5)
ro = re * sf / math.pow(ro, sn)
rs = {}

ra = math.tan(math.pi * 0.25 + geo['lat'] * DEGRAD * 0.5)
ra = re * sf / math.pow(ra, sn)
theta = geo['lon'] * DEGRAD - olon
if theta > math.pi:
  theta -= 2.0 * math.pi
if theta < -math.pi:
  theta += 2.0 * math.pi
theta *= sn
rs['x'] = math.floor(ra * math.sin(theta) + XO + 0.5)
rs['y'] = math.floor(ro - ra * math.cos(theta) + YO + 0.5)

# API Key Value
# API 키 정보
API_key = ''
publicKey = ''

while True:
  # PIR Sensor detected the Motion
  # PIR 센서에서 움직임 감지
  if GPIO.input(pirPin) != 0:
    print('Motion Detected')
    # Get Current Date and Time
    # 현재 날짜와 시간 알아내기
    standard_time = [2, 5, 8, 11, 14, 17, 20, 23] # API Response Time
    time_now = datetime.datetime.now(tz=pytz.timezone('Asia/Seoul')).strftime('%H') # Get Hour
    check_time = int(time_now) - 1
    day_calibrate = 0
    # Hour to API Time
    while not check_time in standard_time:
      check_time -= 1
      if check_time < 2:
        day_calibrate = 1 # Yesterday
        check_time = 23
    
    date_now = datetime.datetime.now(tz=pytz.timezone('Asia/Seoul')).strftime('%Y%m%d') # Get Date
    check_date = int(date_now) - day_calibrate

    # Access to the Weather of hex
    # 조회한 도시의 날씨 데이터에 접근
    owm = OWM(API_key)
    obs = owm.weather_at_coords(geo['lat'], geo['lon'])

    w = obs.get_weather()

    status = w.get_detailed_status()
    temp = w.get_temperature(unit='celsius')
    wind = w.get_wind()
    clouds = w.get_clouds()
    humidity = w.get_humidity()
    rain = w.get_rain()
    snow = w.get_snow()

    # Get Probability of Precipitation from KMA API
    # 기상청에서 강수 확률 정보 가져오기
    url = 'http://newsky2.kma.go.kr/service/SecndSrtpdFrcstInfoService2/ForecastSpaceData?'
    key = 'ServiceKey=' + publicKey
    date = '&base_date=' + str(check_date)
    time = '&base_time=' + str(check_time) + '00'
    nx = '&nx=' + str(int(rs['x']))
    ny = '&ny=' + str(int(rs['y']))
    etc = '&pageNo=1&numOfRows=1'
    api_url = url + key + date + time + nx + ny + etc

    res = requests.get(api_url)
    weatherData = res.text
    bs = BeautifulSoup(weatherData, 'html.parser')
    tag_w = bs.find('fcstvalue')

    # Get Particulate Matter Grade from Public Data API on Korea
    # 공공 데이터에서 미세먼지 정보 가져오기
    dustApiUrl = 'http://openapi.airkorea.or.kr/openapi/services/rest/ArpltnInforInqireSvc/getMsrstnAcctoRltmMesureDnsty?'
    response = requests.get(dustApiUrl)
    dustData = response.text
    soup = BeautifulSoup(dustData, 'html.parser')
    tag_pm10 = soup.find('pm10grade1h')
    tag_pm25 = soup.find('pm25grade1h')

    # Work Ultrasonic Sensor
    # 초음파 센서 작동
    while GPIO.input(pirPin) != 0:
      GPIO.output(trigPin, False)
      sleep(0.5)

      GPIO.output(trigPin, True)
      sleep(0.00001)
      GPIO.output(trigPin, False)
      
      while GPIO.input(echoPin) == 0:
        start_time = datetime.datetime.now().microsecond
      
      while GPIO.input(echoPin) == 1:
        end_time = datetime.datetime.now().microsecond

      duration_time = end_time - start_time

      distance = duration_time * 17000 / 1000000

      if distance >= 0:
        print('Distance: ', distance, 'cm')
        if distance <= 30:
          # Set the Voice comment
          # 음성 멘트 설정
          print('voice')
          TW = 'Today Weather is ' + str(status)
          print(TW)
          T = 'Temperature is ' + str(temp['temp']) + 'degrees in Celsius'
          W = 'Wind is ' + str(wind['speed']) + 'meter per second'
          H = 'Humidity is ' + str(humidity) + 'percent'
          POP = 'Probability of precipitation is ' + tag_w.text + 'percent'

          if tag_pm10.text == '1':
            pm10 = 'Fine particulate matter is good'
          elif tag_pm10.text == '2':
            pm10 = 'Fine particulate matter is normal'
          elif tag_pm10.text == '3':
            pm10 = 'Fine particulate matter is bad'
          elif tag_pm10.text == '4':
            pm10 = 'Fine particulate matter is very bad'

          if tag_pm25.text == '1':
            pm10 = 'Coarse particulate matter is good'
          elif tag_pm25.text == '2':
            pm10 = 'Coarse particulate matter is normal'
          elif tag_pm25.text == '3':
            pm10 = 'Coarse particulate matter is bad'
          elif tag_pm25.text == '4':
            pm10 = 'Coarse particulate matter is very bad'

          ND = 'Have a nice day'

          # Play the Voice comment
          # 음성 멘트 출력
          os.system('echo %s | festival --tts' %TW)
          os.system('echo %s | festival --tts' %T)
          os.system('echo %s | festival --tts' %W)
          os.system('echo %s | festival --tts' %H)
          os.system('echo %s | festival --tts' %POP)
          os.system('echo %s | festival --tts' %pm10)
          os.system('echo %s | festival --tts' %pm25)
          os.system('echo %s | festival --tts' %ND)