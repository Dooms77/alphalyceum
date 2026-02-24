import requests
import xml.etree.ElementTree as ET


URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.xml"


def fetch_high_impact_events():
    r = requests.get(URL, timeout=20)
    r.raise_for_status()

    root = ET.fromstring(r.text)
    events = []
    for item in root.findall("channel/item"):
        title = item.findtext("title", default="")
        desc = item.findtext("description", default="")
        if "High" in desc or "high" in desc:
            events.append({"title": title, "description": desc})
    return events


if __name__ == "__main__":
    events = fetch_high_impact_events()
    for e in events[:20]:
        print(f"- {e['title']}")
