# import the library
from appJar import gui

app = gui("Betsy's Artisanal Android TV Tools", "400x200")

app.addMeter("progress")
app.setMeterFill("progress", "green")
app.setMeter("progress", 50, "I am a test")

app.go()