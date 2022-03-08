from calendar import day_abbr
from tkinter import Tk, ttk, Button, Scale, Canvas, Frame, Label, StringVar, Entry,filedialog
from PIL import Image, ImageTk
import os
import numpy as np
import pandas as pd
import random
from colorutils import hsv_to_hex
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from scipy import spatial

import hike_data_processor

class Paint(object):

    DEFAULT_PEN_SIZE = 5.0
    MAX_WIDTH=1000
    MAX_HEIGHT=500
    DEFAULT_DAYS=1
    MAX_DAYS=30
    DEFAULT_ZOOM=9
    DEFAULT_SERVER=2
    DEFAULT_REST_MILE=10
    DEFAULT_REST_LUNCH=60

    def __init__(self,path):
        self.path=path
        self.tile_server=self.DEFAULT_SERVER
        self.zoom=self.DEFAULT_ZOOM

        self.window = Tk()

        self.scaleImg(self.zoom)
        self.ui_layout(path.name,path.tileServers,path.elevation())
        self.mapCoord_to_canvasCoord()
        self.defaults()

        self.draw_gps_trace()

        self.clear_canvas()

    def start(self):
        self.window.mainloop()

    def scaleImg(self,zoom):
        self.img=self.path.getMap(tile_server=self.tile_server,zoom=zoom)

        #scale image to max window dimensions
        aspect_ratio=self.img.width/self.img.height
        if self.img.width>self.img.height:
            scaled_size=(self.MAX_WIDTH, int(self.MAX_WIDTH/aspect_ratio))
            self.img=self.img.resize(scaled_size)
        elif self.img.height>self.img.width:
            scaled_size=(int(self.MAX_HEIGHT*aspect_ratio), self.MAX_HEIGHT)
            self.img=self.img.resize(scaled_size)
        self.img=ImageTk.PhotoImage(self.img)

        self.width=self.img.width()
        self.height=self.img.height()

        return

    def ui_layout(self,name,tileServers,figure):
        """Defines initial UI layout. Adds widgets to window."""
        self.window.resizable(False,False)

        if name!=None:
            self.window.title(name)
        
        ############## LEFT SECTION (map & elevation plot) ##############
        left=Frame(self.window,bd=3,relief='groove')
        left.grid(row=0,column=0)

        #   <tile frame selection>
        tileFrame=Frame(left,bd=3)
        tileFrame.grid(row=0,column=0,sticky='nsew')

            #   <file input>
        file_input_button=Button(tileFrame,text='Open file',command=self.select_file)
        file_input_button.grid(row=0,column=0,sticky='w')

        self.file_input_entry=Entry(tileFrame)
        self.file_input_entry.grid(row=0,column=1,sticky='w')
            #   </file input>

        tileLabel=Label(tileFrame,text='Map tile server (download speed may vary):')
        tileLabel.grid(row=0,column=2)

        variable=StringVar(left)
        self.tileSelect=ttk.Combobox(tileFrame,textvariable=variable,width=50)
        self.tileSelect['values']=tileServers
        self.tileSelect['state']='readonly'
        self.tileSelect.grid(row=0,column=3,sticky='nsew')   

        zoomLabel1=Label(tileFrame,text='Select zoom level:')
        zoomLabel1.grid(row=0,column=4)

        def update_zoom_label(zoom):
            zoomLabel2=Label(tileFrame,text=zoomScale.get())
            zoomLabel2.grid(row=0,column=6)
        
        zoomScale=Scale(tileFrame,from_=10,to=16,orient='horizontal',showvalue=0,command=update_zoom_label)
        zoomScale.grid(row=0,column=5) 
        zoomScale.set(self.DEFAULT_ZOOM)
        update_zoom_label(self.DEFAULT_ZOOM)

        update_map_button=Button(tileFrame,text='Update map',
                                command=lambda:self.refreshMap(self.tileSelect.current(),zoomScale.get())
                                )
        update_map_button.grid(row=0,column=7,sticky='e')
        #   </tile frame selection>

        #   <canvas>
        canvasFrame=Frame(left,bd=3)
        canvasFrame.grid(row=2,column=0,sticky='nsew')

        self.canvas=Canvas(canvasFrame,width=self.width,height=self.height)
        self.canvas.pack()
        #self.canvas.place(relwidth=0.5,relheight=0.5,anchor='n')
        #   </canvas>

        #   <elevation plot>      
        plot=FigureCanvasTkAgg(figure, master=left)  # A tk.DrawingArea.
        plot.draw()
        plot.get_tk_widget().grid(row=3,column=0)
        #   </elevation plot>

        ############## RIGHT SECTION (paint controls & other buttons) ##############

        right=Frame(self.window,bd=3,relief='flat')
        right.grid(row=0,rowspan=2,column=1,sticky='nsew')
        #right.rowconfigure(0,weight=1)
        right.columnconfigure(0,weight=1)

        #   <paint brush control>
        paint_options=Frame(right,bd=3,relief='groove')
        paint_options.grid(row=0,column=0,sticky='new')
        paint_options.columnconfigure(0,weight=1)

        self.size_scale = Scale(paint_options,from_=20,to=60,resolution=20,orient='horizontal',label='Brush size:')
        self.size_scale.grid(row=0,column=0,sticky='nsew')

        self.clear_button = Button(paint_options, text='Clear Paint',command=self.clear_canvas)
        self.clear_button.grid(row=1,column=0,sticky='nsew')
        #   </paint brush control

        #   <day selection>
        self.dayFrame=Frame(right,bd=3,relief='groove')
        self.dayFrame.grid(row=1,column=0,sticky='nsew')
        self.dayFrame.columnconfigure(0,weight=1)

        dayLabel=Label(self.dayFrame,text='No. days:')
        dayLabel.grid(row=0,column=0,columnspan=2)    

        self.day_input=Entry(self.dayFrame)
        self.day_input.grid(row=1,column=0)
        #   </day selection>

        #   <day data>
        options=Frame(right,bd=3,relief='groove')
        options.grid(row=2,column=0,sticky='sew')
        options.columnconfigure(0,weight=1)

        rest_mile=Label(options,text='Rest per mile (mins): ')
        rest_mile.grid(row=0,column=0)
        self.rest_mile_entry=Entry(options,width=5)
        self.rest_mile_entry.grid(row=0,column=1)

        rest_lunch=Label(options,text='Rest for Lunch (mins): ')
        rest_lunch.grid(row=1,column=0)
        self.rest_lunch_entry=Entry(options,width=5)
        self.rest_lunch_entry.grid(row=1,column=1)

        self.getLinesButton = Button(options, text="Compute Day Stats",command=self.refreshDayDisp)
        self.getLinesButton.grid(row=2,column=0,columnspan=2,sticky='nsew')

        columns=('day','dist','time')
        self.day_disp=ttk.Treeview(options,columns=columns,show='headings')
        self.day_disp.grid(row=3,column=0,columnspan=2,sticky='nsew')

        self.day_disp.column('day',width=30)
        self.day_disp.column('dist',width=50)
        self.day_disp.column('time',width=50)

        self.day_disp.heading('day',text='Day')
        self.day_disp.heading('dist',text='Distance\n(miles)\n')
        self.day_disp.heading('time',text='Time\n(hrs)\n')
        #   </day data>

        return    

    def defaults(self):
        """Defines default values & keybinds."""
        self.old_x, self.old_y = None, None
        self.active_button = None
        self.size_multiplier = 1
        self.lineList=[]  

        self.add_image()
        self.canvas.bind('<B1-Motion>', self.paint)  #   Binds paint function to mouse motion when mousebutton1 clicked. Passes event object eg. event.x, event.y
        self.canvas.bind('<ButtonRelease-1>', self.reset)
        self.day_input.bind('<Return>',lambda event: self.update_day_buttons(self.day_input.get()))

        self.tileSelect.current(self.tile_server)

        self.day_buttons=[]
        self.day_input.insert(0,str(self.DEFAULT_DAYS))
        self.update_day_buttons(self.DEFAULT_DAYS)
        self.rest_lunch_entry.insert(0,str(self.DEFAULT_REST_LUNCH))
        self.rest_mile_entry.insert(0,str(self.DEFAULT_REST_MILE))
        self.colour=self.colour_list[0]
        self.day=0

        self.line_start = (None, None)

    def select_file(self):
        filetypes=[('*.gpx *.kmz *kml')]
        filename=filedialog.askopenfilename(title='Open a file',initialdir=os.getcwd(),filetypes=filetypes)
        self.file_input_entry.insert(0,filename)

        return

    def update_day_buttons(self,days):
        try:    #   does nothing if input is not int
            days=int(days)
        except:
            return

        #   Deletes buttons and widgets from frame
        if len(self.day_buttons)!=0:
            for widget in self.dayFrame.grid_slaves():  #   Gets widgets assigned to dayFrame
                if int(widget.grid_info()['row'])>1:    #   Skips input box
                    widget.grid_forget()                #   Removes widget from frame

        self.colour_list=[self.generateColour(id) for id in np.linspace(0,256,days)]    #   Generate colours

        self.day_buttons=[] #   Resets button list
        for day in range(days):   
            #   Updates buttons         
            self.day_buttons.append(Button(self.dayFrame,
                                    bg=self.colour_list[day],
                                    command=lambda colour=self.colour_list[day],day=day: self.set_day(day,colour)
                                    ))
            self.day_buttons[day].grid(row=day+2,column=0,sticky='nsew')
            
            #   Updates label
            day_label=Label(self.dayFrame,text=f'Day {day+1}')
            day_label.grid(row=day+2,column=1,sticky='nsew')

            #   Recolours lines
            if self.lineList!=[]:
                for line in self.lineList:
                    line_day=int(self.canvas.gettags(line)[1])  #   gets day tag from line on canvas
                    if line_day>=days:  #   if the line is for a day that has been removed
                        self.canvas.delete(line)
                        self.lineList.remove(line)
                    if line_day==day:
                        self.canvas.itemconfig(line,fill=self.colour_list[day]) #   recolours line

        return

    def refreshMap(self,tile_server,zoom):
        self.tile_server=tile_server
        self.scaleImg(zoom)
        self.canvas.delete('all')
        self.lineList=[] 
        self.add_image()
        self.mapCoord_to_canvasCoord()
        self.draw_gps_trace()

        return

    def add_image(self):
        self.canvas.create_image(self.width/2,self.height/2,image=self.img,tags='image')

    def mapCoord_to_canvasCoord(self):
        "Converts gps trace map coordinates to tkinter canvas coordinates"
        
        wscale=self.width/(self.path.x1-self.path.x0) #   Scale factor between map coordinates & canvas
        hscale=self.height/(self.path.y1-self.path.y0)

        self.gps_trace=[]   #   In canvas coordinates!
        for index,row in self.path.hikeData.iterrows():
            x,y=self.path.coord_to_pixels(row['lat'],row['lon'],tile_size=self.path.TILE_SIZE)    #   Gets gps trace coordinates
            
            x_=(x-self.path.x0)*wscale
            y_=self.height+(y-self.path.y1)*hscale #   Canvas origin is in top left, i.e. x0,y1 in map coordinates

            self.gps_trace.append([x_,y_,])

        self.gps_trace=np.array(self.gps_trace)

        return

    def generateColour(self,n):
        hue=n
        sat=0.7
        vib=0.9

        return hsv_to_hex((hue,sat,vib))

    def draw_gps_trace(self):
        for i,_ in enumerate(self.gps_trace):
            if i+1!=len(self.gps_trace):    #   stops 1 before the end
                self.canvas.create_line(self.gps_trace[i,0],self.gps_trace[i,1],self.gps_trace[i+1,0],self.gps_trace[i+1,1],
                                    width=3, fill='black',
                                    capstyle='round', smooth=True, splinesteps=36,
                                    tags='gps_trace')
        
        return

    def clear_canvas(self):
        self.canvas.delete("line")
        self.lineList=[]    

    def paint(self, event):
        """Handles painting on canvas."""

        line_width = self.size_scale.get() * self.size_multiplier
        paint_colour = self.colour #   erasor uses same function as paint, just with white colour
        day=self.day
        if self.old_x and self.old_y:
            self.lineList.append(self.canvas.create_line(self.old_x, self.old_y, event.x, event.y,    #   Connects last mouse coords with current mouse coords
                               width=line_width, fill=paint_colour,
                               capstyle='round', smooth=True, splinesteps=36,
                               stipple='gray75',
                               tags=("line",day,line_width)))
        
        self.old_x = event.x
        self.old_y = event.y

    def reset(self, event=None):
        self.old_x, self.old_y = None, None

    def set_day(self,day,colour):
        self.day=day
        self.colour=colour

    def getPaintData(self):
        # canvas.coords in format [x0,y0,x1,y1]
        paintCoords=[]
        paintColours=[]
        paintRadius=[]
        for i,line in enumerate(self.lineList):
            if i==0:    #   start coordinate
                x=self.canvas.coords(self.lineList[i])[0]
                #y=self.canvas.winfo_height()-self.canvas.coords(self.lineList[i])[1]
                y=self.canvas.coords(self.lineList[i])[1]

                paintCoords.append([x,y])
            else:
                x=self.canvas.coords(line)[2]
                #y=self.canvas.winfo_height()-self.canvas.coords(line)[3]
                y=self.canvas.coords(line)[3]

                paintCoords.append([x,y])   #   gets end coordinate of each line

            paintColours.append(self.canvas.gettags(line)[1])
            paintRadius.append(float(self.canvas.gettags(line)[2])/2)

        paint_data=pd.DataFrame(data=paintCoords,columns=['x','y'])
        paint_data['day']=paintColours
        paint_data['radius']=paintRadius

        return paint_data

    def find_neighbour(self,point,point_array):
        """Employes a KDTree to find nearest neighbour"""
        distance,nearestIndex=spatial.KDTree(point_array).query(point)

        return distance,nearestIndex

    def calcDays(self):
        paint_data=self.getPaintData()
        #print(paint_data)
        #print(f"\n{self.gps_trace}")
        gps_day=[]
        for i,coord in enumerate(self.gps_trace):
            distance,index=self.find_neighbour(coord,paint_data[['x','y']]) #   finds 
            paint_radius=paint_data.iloc[index]['radius']

            if distance<=paint_radius:
                #print(f"{paint_data.iloc[index][['x','y']]}|{coord}")
                gps_day.append(int(paint_data.iloc[index]['day']))
            else:
                gps_day.append(pd.NA)
        self.path.hikeData['day']=gps_day
        
        day_data=self.path.calcDayData()

        return day_data

    def refreshDayDisp(self):
        if len(self.lineList)==0:
            return

        day_data=self.calcDays()
        if self.day_disp.get_children()!=():
            self.day_disp.delete(*self.day_disp.get_children())

        for index,row in day_data.iterrows():
            self.day_disp.insert('','end',values=(int(row['day']+1),
                                                round(row['dist'],1),
                                                round(row['time']+row['dist']*float(self.rest_mile_entry.get())/60+float(self.rest_lunch_entry.get())/60,1)
                                                ))

if __name__ == '__main__':
    os.system('cls')

    input_file="Dartmoor 2.kmz"
    path=hike_data_processor.Path(input_file)
    ui=Paint(path)
    ui.start()