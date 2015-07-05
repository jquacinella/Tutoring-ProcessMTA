import csv
import pprint
import datetime
import pickle
from dateutil.parser import parse
import math
import matplotlib.pyplot as plt
import numpy as np

data = { }
numKeys = 0
counter = 0
oldKey = None
first = True

debug = False
# debug = True

# Try to read in data from pickle file
try:
    print "Trying to load via pickle"
    data = pickle.load(open("data.pkl", "rb"))
    print "Done loading via pickle"
    print
except Exception as e:
    pass

# IF we couldn't, load manually from txt file
if not data:
    # Open the CSV and skip header line
    print "No pickle file found, starting from scratch"
    f = open("turnstile_150613.txt", "r")
    f.next()

    # Loop over every line in the CSV
    reader = csv.reader(f)
    for row in reader:   
        # Key into our dict is the first 4 columns
        key = tuple(row[:4])

        # Only get one key for now
        if oldKey != key:
            numKeys = numKeys + 1
            print "Num keys = %d, num rows = %d" % (numKeys, counter)

        # Store as new key or append to list
        if key in data:
            data[key].append(row[4:])
        else:
            data[key] = [ row[4:] ]

        # Update state variables
        oldKey = key
        counter = counter + 1

    # Print data so far
    print "Done loading data!"
    print

    # Next step is to get rid of some data from each row
    print "Starting step one"
    for turnstile in data:
        newRows = []
        for row in data[turnstile]:
            newRows.append( ( parse("%s %s" % (row[2], row[3])), int(row[5]), int(row[6])) )
        data[turnstile] = newRows

    # Print data so far
    print "Done w/ step one"
    print

    # Next step is to get data per time period, not cumulative
    print "Starting step two"
    for turnstile in data:
        newRows = []

        for rowIdx in range(len(data[turnstile]) - 1):
            row = data[turnstile][rowIdx]
            nextRow = data[turnstile][rowIdx + 1]
            enters = nextRow[1] - row[1]
            exits = nextRow[2] - row[2]

            newRows.append((row[0], enters, exits))
        data[turnstile] = newRows

    print "Done w/ step two"
    print

    print "Pickling results"
    pickle.dump(data, open("data.pkl", "wb"))
    print "Done pickling"
    print

# Now we have a data dictionary, we need to transform it into a multi level
# dict that maps station to turnstiles, and a turnstile to its rows of data
perStationData = { }
print "Transforming data into per-station dict"
for turnstile in data:
    # The key is made up of 4 fields, so break it apart
    (controlArea, unit, scp, station) = turnstile

    # The station is identified by only three values
    station = (controlArea, unit, station)

    # SCP identifies a single turnstile at a station, so setup dictionary
    if station in perStationData:
        perStationData[station][scp] = data[turnstile]
    else:
        perStationData[station] = { scp: data[turnstile] }
print "Done transforming data into per-station dict"
print

print "Pickling per-station results"
pickle.dump(perStationData, open("data-per-station.pkl", "wb"))
print "Done pickling per-station results"
print


# Now that we have the data in a conveinent form, we need to start
# summing the values within the right time frame for morning and evening
print "Start calculating sums of evening entries and morning exits"
perStationSums = { }
for station in perStationData:

    # If we have never seen this station, setup empty dict for it
    if station not in perStationSums:
        perStationSums[station] = { }
    
    # These dicts map a date to the approriate sum for this station
    sumEveningEntries = { }     # datetime => sum for day
    sumMorningExits = { }

    # For all turnstiles in the station ...
    for turnstile in perStationData[station]:
        # If we have never seen this turnstile at this station, setup empty dict for it
        if turnstile not in perStationSums[station]:
            perStationSums[station][turnstile] = { }

        # For each datapoint
        for entry in perStationData[station][turnstile]:
            # Record the date and time
            date = entry[0].date()
            time = entry[0].time()

            # Setup first record in summation dict if need be
            if date not in sumEveningEntries:
                sumEveningEntries[date] = 0

            # If past 4pm and before 8pm, sum the evening tally
            if time.hour >= 16 and time.hour < 20:
                sumEveningEntries[date] += entry[1]

            # Setup first record in summation dict if need be
            if date not in sumMorningExits:
                sumMorningExits[date] = 0

            # If past 8am and before 12pm, sum the morning tally
            if time.hour >= 8 and time.hour < 12:
                sumMorningExits[date] += entry[2]

        # Store sums in dict that maps turnstile to its daily evening and morning sums
        perStationSums[station][turnstile] = {"evening": sumEveningEntries,
                                            "morning": sumMorningExits}
print "Done transforming data into per-station-sums dict"
print

print "Pickling per-station sums"
pickle.dump(perStationSums, open("data-per-station-sums.pkl", "wb"))
print "Done pickling per-station sums"
print



# We now average the summations for weekdays
print "Start calculating avgs of evening entries and morning exits per station"
dataPerStationAvgs = { }
for station in perStationSums:

    if station not in dataPerStationAvgs:
        dataPerStationAvgs[station] = { }
    
    sumEveningEntries = 0
    sumMorningExits = 0
    for turnstile in perStationSums[station]:
        for date in perStationSums[station][turnstile]['evening']:
            if date.isoweekday() <= 5:
                sumEveningEntries += perStationSums[station][turnstile]["evening"][date]
        
        for date in perStationSums[station][turnstile]['morning']:
            if date.isoweekday() <= 5:
                sumMorningExits += perStationSums[station][turnstile]["morning"][date]

    dataPerStationAvgs[station] = { "eveningAvg": sumEveningEntries / 5.0, "morningAvg": sumMorningExits / 5.0 }
print "Done transforming data into per-station-avgs dict"
print

print "Pickling per-station avgs"
pickle.dump(dataPerStationAvgs, open("data-per-station-avgs.pkl", "wb"))
print "Done pickling per-station avgs"



###
### Plotting time
###

### Evening

# Generate a list of tuples of x, y values, where x = station name and y = weekday evening avg
eveningValues = [ ("%s-%s-%s" % key,  dataPerStationAvgs[key]["eveningAvg"]) for key in dataPerStationAvgs if dataPerStationAvgs[key]["eveningAvg"] > 0]

# Sort them by average
sortedEveningValues = sorted(eveningValues, key=lambda tup: tup[1], reverse=True)

# Generate x axis labels, which are station names
# (in this case we print every other 5 stations for readability)
labelsEvenings = []
for idx, x in enumerate(sortedEveningValues):
    if idx % 5 == 0:
        labelsEvenings.append(x[0].split('-')[-1])
    else:
        labelsEvenings.append('')

# Generate a bar plot, resize to maximum, save and close
fig, ax = plt.subplots()
rects1 = ax.bar(np.arange(len(sortedEveningValues)), [x[1] for x in sortedEveningValues], .5, color='r')
plt.xticks(np.arange(0, len(sortedEveningValues), 1), labelsEvenings, rotation='vertical', fontsize=8 )
plt.xlabel("Station")
plt.ylabel("Evening Avg")
plt.title("Avg Weekday Evening Entries per MTA Station")
# mng = plt.get_current_fig_manager()
# mng.resize(*mng.window.maxsize())
# fig.set_size_inches(16, 10)
# plt.savefig('evening-entries.png')
plt.close()


### Morning

# Generate a list of tuples of x, y values, where x = station name and y = weekday morning avg
morningValues = [ ("%s-%s-%s" % key,  math.log(dataPerStationAvgs[key]["morningAvg"])) for key in dataPerStationAvgs if dataPerStationAvgs[key]["morningAvg"] > 0]

# Sort them by average
sortedMorningValues = sorted(morningValues, key=lambda tup: tup[1], reverse=True)

# Generate x axis labels, which are station names
# (in this case we print every other 5 stations for readability)
labelsMornings = []
for idx, x in enumerate(sortedMorningValues):
    if idx % 5 == 0:
        labelsMornings.append(x[0].split('-')[-1])
    else:
        labelsMornings.append('')

# Generate a bar plot, resize to maximum, save and close
fig, ax = plt.subplots()
rects1 = ax.bar(np.arange(len(sortedMorningValues)), [x[1] for x in sortedMorningValues], .5, color='r')
plt.xticks(np.arange(0, len(sortedMorningValues), 1), labelsMornings, rotation='vertical', fontsize=8 )
plt.xlabel("Station")
plt.ylabel("Log of the Morning Avg")
plt.title("Avg Weekday (Log) Morning Exits per MTA Station")
# mng = plt.get_current_fig_manager()
# mng.resize(*mng.window.maxsize())
# fig.set_size_inches(16, 10)
# plt.savefig('morning-exits.png')
plt.close()








### Totals

# Generate a list of tuples of x, y values, where x = station name and y = weekday morning avg
totalValues = [ ("%s-%s-%s" % key,  math.log(dataPerStationAvgs[key]["morningAvg"] + dataPerStationAvgs[key]["eveningAvg"])) 
                for key in dataPerStationAvgs 
                if dataPerStationAvgs[key]["morningAvg"] + dataPerStationAvgs[key]["eveningAvg"] > 0]

# Sort them by average
sortedTotalValues = sorted(totalValues, key=lambda tup: tup[1], reverse=True)

# Generate x axis labels, which are station names
# (in this case we print every other 5 stations for readability)
labelsTotals = []
for idx, x in enumerate(sortedTotalValues):
    if idx % 5 == 0:
        labelsTotals.append(x[0].split('-')[-1])
    else:
        labelsTotals.append('')

# Generate a bar plot, resize to maximum, save and close
fig, ax = plt.subplots()
rects1 = ax.bar(np.arange(len(sortedTotalValues)), [x[1] for x in sortedTotalValues], .5, color='r')
plt.xticks(np.arange(0, len(sortedTotalValues), 1), labelsTotals, rotation='vertical', fontsize=8 )
plt.xlabel("Station")
plt.ylabel("Log of the Total Avg")
plt.title("Avg Weekday (Log) Totals per MTA Station")
# mng = plt.get_current_fig_manager()
# mng.resize(*mng.window.maxsize())
fig.set_size_inches(16, 10)
plt.savefig('total-exits.png')
plt.close()