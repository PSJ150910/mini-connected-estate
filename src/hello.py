import csv


def read_rooms(path):
    """Read the rooms CSV and return a list of room dictionaries."""
    rooms = []
    with open(path) as file:
        for row in csv.DictReader(file):
            row["temperature_c"] = float(row["temperature_c"])  # text -> number
            rooms.append(row)  # add this room to the end of the list
    return rooms


def find_warmest(rooms):
    """Return the room with the highest temperature."""
    warmest = rooms[0]  # start by assuming the first room is warmest
    for room in rooms:
        if room["temperature_c"] > warmest["temperature_c"]:
            warmest = room  # found a warmer one, so it takes the lead
    return warmest


def find_coldest(rooms):
    """Return the room with the lowest temperature."""
    coldest = rooms[0]  # start by assuming the first room is coldest
    for room in rooms:
        if room["temperature_c"] < coldest["temperature_c"]:
            coldest = room  # found a colder one, so it takes the lead
    return coldest


rooms = read_rooms("data/rooms.csv")
warmest = find_warmest(rooms)
print(
    f"Warmest room: {warmest['name']} ({warmest['room_id']}) at {warmest['temperature_c']} C"
)
coldest = find_coldest(rooms)
print(
    f"Coldest room: {coldest['name']} ({coldest['room_id']}) at {coldest['temperature_c']} C"
)
