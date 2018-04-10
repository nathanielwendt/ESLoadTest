import sys
import csv
from numpy import mean,median,std,var

class Entry(object):
    def __init__(self, duration, cat_size):
        self.duration = duration
        self.cat_size = cat_size

if __name__ == "__main__":
    file = sys.argv[1]
    with open(file, 'rb') as csv_file_data:
        csvreader = csv.reader(csv_file_data)
        entries = []
        for line in csvreader:
            try:
                if "*" not in line:# and "6936022" not in line and "6936021" not in line:
                    entries.append(Entry(int(line[0]), int(line[1])))
            except:
                pass

        entries_durations = [entry.duration for entry in entries]

        mean = mean(entries_durations)
        median = median(entries_durations)
        variance = var(entries_durations)
        min_dur = min(entries_durations)
        max_dur = max(entries_durations)
        print "min_dur: {0}, max_dur: {1}, mean: {2}, median: {3}, variance: {4}".format(min_dur, max_dur, mean, median, variance)
