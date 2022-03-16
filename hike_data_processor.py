from enum import unique
import zipfile
import xml.etree.ElementTree as ET
import requests
import os.path
import time
import pandas as pd
import numpy as np
from matplotlib import pyplot as plt
from io import BytesIO
from PIL import Image
from tqdm import tqdm

class Path():
    DEFAULT_ZOOM=13 #   for running without UI
    TILE_SIZE=256   #   map tile size in px

    def __init__(self,name=None):
        self.name=name
        self.tileServers=(
            "https://c.tile.opentopomap.org", #   VERY slow on occasion 
            "https://tile.openstreetmap.org", #   Fast, basic, no topography
            "https://a.tile-cyclosm.openstreetmap.fr/cyclosm" #   Fast, has topography, weird colouring
        )

        return

    def input(self,file):
        """Detects input file format & calls relevant import function"""
        self.filetype=os.path.splitext(file)[1]
        if self.filetype==".gpx":
            coordinates,self.name=self.gpxImport(file)
        if self.filetype==".kmz":
            kml=self.kmzImport(file)
            coordinates,self.name=self.kmlImport(kml)
        if self.filetype==".kml":
            coordinates,self.name=self.kmlImport(file)

        self.hikeData=pd.DataFrame(data=coordinates,columns=['lat','lon'])
        self.hikeData['lat_rad']=self.hikeData['lat'].apply(np.radians)
        self.hikeData['lon_rad']=self.hikeData['lon'].apply(np.radians)

        return

    def elevation(self):
        """Handles elevation routine. Returns pyplot object."""
        self.getElevations()
        self.calcDist()
        self.calcSlope()
        self.calcSpeed()
        self.calcTime()
        elevationPlot=self.plotElevation()

        return elevationPlot

    def kmzImport(self,file):
        """Unzips kmz file."""
        archive = zipfile.ZipFile(file, 'r')
        kml=archive.open('doc.kml','r')

        return kml

    def kmlImport(self,file):
        """Reads kml file. Gets path name, lat & lon coordinates. kml files are in xml format"""
        root = ET.parse(file).getroot()
        namespace=root.tag.split('}')[0]+'}'
        doc=root.findall(f"{namespace}Document")[0]

        placemark=doc.findall(f"{namespace}Placemark")[0]
        name=placemark.findall(f"{namespace}name")[0].text
        lineString=placemark.findall(f"{namespace}LineString")[0]
        points=lineString.findall(f"{namespace}coordinates")[0].text.strip().split(' ')    #   comes out in lon,lat
        points=[point[:-2] for point in points] #   removes null altitude

        coordinates=[]
        for point in points:
            coordinates.append([float(point.split(',')[1]),float(point.split(',')[0])]) #   [lon,lat]
        coordinates=np.array(coordinates,dtype=float)

        return coordinates, name

    def gpxImport(self,file):
        """Reads gpx file. Gets path name, lat & lon coordinates. gpx files are in xml format"""
        root=ET.parse(file).getroot()
        namespace=root.tag.split('}')[0]+'}'

        trk=root.findall(f"{namespace}trk")[0]
        name=trk.findall(f"{namespace}name")[0].text
        trkseg=trk.findall(f"{namespace}trkseg")[0]

        coordinates=[]
        for point in trkseg:
            coordinates.append([float(point.attrib['lat']),float(point.attrib['lon'])])
        coordinates=np.array(coordinates,dtype=float)

        return coordinates,name

    def getElevations(self):
        """Gets altitude data along line from opentopodata api"""
        n=100   #   100 API requests per call max
        coordChunks=[self.hikeData[['lat','lon']].to_numpy()[i:i+n] for i in range(0,len(self.hikeData.index),n)]
        url='https://api.opentopodata.org/v1/eudem25m?'
        
        elevations=[]  #   FORMAT: lat,lon,alt
        print("Downloading elevation data...")
        for chunk in tqdm(coordChunks):
            params="locations="+"|".join(",".join(str(n) for n in pair) for pair in chunk)
            response=requests.get(url+params)

            results=response.json()['results']
            for result in results:
                elevations.append(float(result['elevation']))
            
            time.sleep(0.34) #   3 calls per second max
        elevations=np.array(elevations)

        self.hikeData['alt']=elevations

        return

    def calcDist(self):
        """Calculates distance between coordinates."""
        dist=[] #   UNITS: miles
        distSum=[]
        for i,row in self.hikeData.iterrows():
            if i==0:
                dist.append(0)
                distSum.append(0)
                continue

            lat0=self.hikeData['lat_rad'][i-1]
            lat1=self.hikeData['lat_rad'][i]
            lon0=self.hikeData['lon_rad'][i-1]
            lon1=self.hikeData['lon_rad'][i]

            d=2*6371*np.arcsin(np.sqrt((np.sin((lat1-lat0)/2)**2+np.cos(lat0)*np.cos(lat1)*np.sin((lon1-lon0)/2)**2)))/1.6  #   equation from wikipedia somewhere
            dist.append(float(d))
            distSum.append(float(distSum[i-1]+d))

        self.hikeData['dist']=dist
        self.hikeData['distSum']=distSum

        self.distSum=distSum[-1]

        return

    def calcSlope(self):
        """Calculates slope between coordinates"""
        slope=[]    #   UNITS: %
        for i,row in self.hikeData.iterrows():
            if i==0:
                slope.append(0)
                continue
            
            alt0=self.hikeData['alt'][i-1]
            alt1=self.hikeData['alt'][i]
            slope.append(float(100*(alt1-alt0)/(row['dist']*1600)))

        self.hikeData['slope']=slope

    def calcSpeed(self):
        """Calculates walking speed according to slope."""
        posGrad=-0.0469 #   from linear curve fitted to strava data
        negGrad=0.0265
        neutral=2.7 #   mph

        speed=[]    #   UNITS: mph
        for i,row in self.hikeData.iterrows():
            if i==0:
                speed.append(0)
                continue

            if row['slope']>0:
                v=posGrad*row['slope']+neutral
            else:
                v=negGrad*row['slope']+neutral
            if v<0.3:
                v=0.3
            
            speed.append(float(v))
        
        #smoothes speed data
        box_pts=4   #   colects 4 points to 1
        box=np.ones(box_pts)/box_pts
        speed_smooth=list(np.convolve(speed[1:],box,mode='same'))
        speed_smooth[0]=speed[1]
        speed_smooth[-1]=speed[-1]

        self.hikeData['speed']=speed
        self.hikeData['speed_smooth']=[0]+speed_smooth

    def calcTime(self):
        """Calculates walking time between coordinates"""
        time=[]    #   UNITS: hrs
        for i,row in self.hikeData.iterrows():
            if i==0:
                time.append(0)
                continue
                
            time.append(float(row['dist']/row['speed']))
        self.hikeData['time']=time
        self.timeSum=sum(time[1:])

    def plotElevation(self):
        """Plots elevation. Returns matplotlib pyplot object."""
        fig,ax=plt.subplots(figsize=(10,3))
        ax.plot(self.hikeData['distSum'][1:],self.hikeData['alt'][1:],color='k',linewidth=1,label="Altitude")
        ax.set_xlabel("Total Distance (miles)")
        ax.set_ylabel("Altitude (m)")

        ax2=ax.twinx()
        #ax2.plot(self.hikeData['distSum'][1:],self.hikeData['speed'][1:],color='b',linewidth=1)
        ax2.plot(self.hikeData['distSum'][1:],self.hikeData['speed_smooth'][1:],color='r',linewidth=1,label="Walking Speed")
        ax2.set_ylabel("Walking Speed (mph)")

        fig.tight_layout()
        ax2.yaxis.label.set_color('r')

        return fig

    def coord_to_pixels(self,lat,lon,tile_size):
        """convert gps coordinates to web mercator"""

        r = np.power(2, self.zoom) * tile_size
        lat = np.radians(lat)

        x = (lon + 180.0) / 360.0 * r  #   Equations in openstreetmap wiki
        y = (1.0 - np.log(np.tan(lat) + (1.0 / np.cos(lat))) / np.pi) / 2.0 * r

        return x, y

    def getMap(self,tile_server,zoom=None):
        """"Gets map tiles (see openstreetmap wiki) for path area."""
        if zoom==None:
            self.zoom=self.DEFAULT_ZOOM
        else:
            self.zoom=zoom

        #   min & max gps coordiantes
        top,bot=self.hikeData['lat'].max(),self.hikeData['lat'].min()
        left,right=self.hikeData['lon'].min(),self.hikeData['lon'].max()

        #   min & max map coordinates - see openstreetmap wiki
        self.x0,self.y1=self.coord_to_pixels(bot,left,self.TILE_SIZE)  #   y0,y1 flipped because latitude increases towards equator
        self.x1,self.y0=self.coord_to_pixels(top,right,self.TILE_SIZE)

        #   calcualtes tile dimensions
        x0_tile=int(self.x0/self.TILE_SIZE)
        y0_tile=int(self.y0/self.TILE_SIZE)
        y1_tile=int(np.ceil(self.y1/self.TILE_SIZE))
        x1_tile=int(np.ceil(self.x1/self.TILE_SIZE))

        #   Initiates image with size of tiles combined
        img=Image.new('RGB',(
            abs(x1_tile-x0_tile)*self.TILE_SIZE,
            abs(y1_tile-y0_tile)*self.TILE_SIZE
        ))

        host=self.tileServers[tile_server]

        tasks=[]
        for x_tile in range(x0_tile,x1_tile):
            for y_tile in range(y0_tile,y1_tile):
                tasks.append((x_tile,y_tile))

        #   Gets map tiles from api
        print("Downloading map tiles...")
        for task in tqdm(tasks):
            x_tile,y_tile=task
            try:
                with requests.get("{host}/{z}/{x}/{y}.png".format(host=host,x=x_tile, y=y_tile, z=self.zoom)) as response:
                    tile_img = Image.open(BytesIO(response.content))
            except TimeoutError as error:
                print(error)
                print("\nMap tile server time out. Try another tile server: https://wiki.openstreetmap.org/wiki/Tiles")
                exit()

            #   stacks tiles
            img.paste(
                im=tile_img,
                box=((x_tile-x0_tile)*self.TILE_SIZE,(y_tile-y0_tile)*self.TILE_SIZE)
                )

        #   crops tiles to original min/max coordinates
        x=x0_tile*self.TILE_SIZE
        y=y0_tile*self.TILE_SIZE
        img=img.crop((
            int(self.x0-x),  #   left
            int(self.y0-y),  #   top
            int(self.x1-x),  #   right
            int(self.y1-y)   #   bottom
            ))

        self.aspect_ratio=0.9*(self.x1-self.x0)/(self.y1-self.y0)
        self.left,self.right,self.bot,self.top=left,right,bot,top

        return img

    def plotMap(self,img):
        """Plots map tiles & path."""

        fig,ax=plt.subplots()
        ax.imshow(img,extent=(self.left,self.right,self.bot,self.top))
        ax.set_aspect(self.aspect_ratio) #   idk why but when transforming to lon/lat the aspect ratio is messed up - this is a botch fix
        ax.plot(self.hikeData['lon'],self.hikeData['lat'],color='r',linewidth=2)
        
        #ax.set_ylim(bot,top)
        #ax.set_xlim(left,right)
        ax.set_xlabel('Longitude (deg)')
        ax.set_ylabel('Latitude (deg)')

        #fig.tight_layout()

        return plt

    def calcDayData(self):
        """Calculates distance and time of each day. Requires 'day' data in hikeData."""

        day_data=self.hikeData.dropna(subset=['day'])
        day_data=day_data.groupby(by=['day'],as_index=False).sum()[['day','dist','time']]

        return day_data

if __name__=="__main__":
    os.system('cls')
    path=Path()
    path.input('gpx.gpx')
    #pathPlot=path.elevation()
    #print(path.coordinates)
    print(path.hikeData)
    img=path.getMap(tile_server=2,zoom=13)
    img.show()
    #map_plot=path.plotMap(img)
    #plt.show()
