import csv

with open("data/rooms.csv") as file:
    reader = csv.DictReader(file)
    for row in reader:
        print(row)
