import json
import csv
import copy

def loadData():
    segments = {}
    segments["site_title"] = loadHTML("./data/site_title.html")
    segments["title"] = loadHTML("./data/title.html")
    segments["description"] = loadHTML("./data/description.html")
    segments["short_description"] = loadHTML("./data/short_description.html")
    segments["_news"] = loadHTML("./data/news.html")
    segments["_experience"] = loadHTML("./data/experience.html")
    segments["_contact"] = loadHTML("./data/contact.html")

    segments["pubs"] = loadJson("./data/pubs.json")
    segments["person"] = loadCSV("./data/person.csv")
    segments["conference"] = loadCSV("./data/conference.csv")
    
    segments["_template"] = loadHTML("./data/template/template.html")
    segments["_pubs_template"] = loadHTML("./data/template/pubs_template.html")
    segments["_single_pub_template"] = loadHTML("./data/template/single_pub_template.html")
    return segments

def loadCSV(filename):
    with open(filename) as f:
        csv_reader = csv.reader(f)

        # Get all model ids from the csv file
        dict = {}
        index = 0
        for line in csv_reader:
            if index == 0:
                index += 1
                continue
            dict[line[0]] = line[2]

        return dict
        

def loadJson(filename):
    with open(filename) as f:
        return json.load(f)

def loadHTML(filename):
    with open(filename) as f:
        lines = f.readlines()
    return [line.strip("\n") for line in lines]

def generateHTML(template, segments, out=True, output_filename=""):
    new_html = []

    for line in template:
        if line.strip(" ")[:8] == "[!!TODO]":
            segment_name = line.strip(" ").strip("\n").split(" ")[1]
            if segment_name in segments:
                new_html += segments[segment_name]
        else:
            new_html.append(line.strip("\n"))
    if out:
        with open(output_filename, "w") as f:
            f.write("\n".join(new_html))
    else:
        return new_html

def parseNews(news, short=True):
    lines = ["<p>", "<h3>News</h3>", "<ul>"]
    lines += news
    lines += ["</ul>"]
    if short == True:
        lines+= ["<a href=\"news.html\">More...</a>"]
    lines += ["</p>"]
    return lines

def parsePubs(segments):
    all_pubs = []
    for pub in segments["pubs"]:
        info = {}
        info["image"] = [f"<a href=\"#\"><img src={pub['image']} alt=\"image\" class=\"img-responsive\" style=\"width: 300px;\" /></a>"]
        content = []
        index = 0
        for author in pub['authors']:
            index += 1
            if index == len(pub['authors']):
                if segments['person'][author] == "ME" or segments['person'][author] == "":
                    content.append(f"<strong>{author}</strong><br>")
                elif segments['person'][author] == "":
                    content.append(f"{author}<br>")
                else:
                    content.append(f"<a href={segments['person'][author]} target=\"_blank\">{author}</a><br>")
            else:
                if segments['person'][author] == "ME":
                    content.append(f"<strong>{author}</strong>,")
                elif segments['person'][author] == "":
                    content.append(f"{author},")
                else:
                    content.append(f"<a href={segments['person'][author]} target=\"_blank\">{author}</a>,")
        content.append(f"<h3 class=\"purple\">{pub['name']}</h3>")
        content.append(f"<a href={segments['conference'][pub['conference']]} target=\"_blank\">{pub['conference']}</a>")
        if pub["special"] == "oral":
            content[-1] += ", <i style=\"color: red\">Oral Presentation</i>"
        elif pub["special"] == "spotlight":
            content[-1] += ", <i style=\"color: red\">Spotlight</i>"
        # content.append(f"<p>{pub['description']}</p>")
        if pub["paper"] != "":
            content.append(f"<a href={pub['paper']} target=\"_blank\">[Paper]</a>")
        if pub["project"] != "":
            content.append(f"<a href={pub['project']} target=\"_blank\">[Project]</a>")
        if pub["code"] != "":
            content.append(f"<a href={pub['code']} target=\"_blank\">[Code]</a>")

        info["content"] = content
        all_pubs += generateHTML(segments["_single_pub_template"], info, False)
        all_pubs.append("<br>")
        
    pubs = {"pubs": all_pubs}
    return generateHTML(segments["_pubs_template"], pubs, False)

def generateIndexHTML(segments):
    segments["body_1"] = parseNews(segments["_news"][:6], True)
    segments["body_2"] = parsePubs(segments)
    generateHTML(segments["_template"], segments, True, "./index.html")

def generateNewsHTML(segments):
    segments["body_1"] = parseNews(segments["_news"], False)
    generateHTML(segments["_template"], segments, True, "./news.html")

def generatePublicationsHTML(segments):
    segments["body_2"] = parsePubs(segments)
    generateHTML(segments["_template"], segments, True, "./pubs.html")

def generateExperienceHTML(segments):
    segments["body_1"] = segments["_experience"]
    generateHTML(segments["_template"], segments, True, "./experience.html")

def generateContactHTML(segments):
    segments["body_2"] = segments["_contact"]
    generateHTML(segments["_template"], segments, True, "./contact.html")

if __name__ == '__main__':

    base_segments = loadData()
    
    generateIndexHTML(copy.deepcopy(base_segments))
    generateNewsHTML(copy.deepcopy(base_segments))
    generatePublicationsHTML(copy.deepcopy(base_segments))
    generateExperienceHTML(copy.deepcopy(base_segments))
    generateContactHTML(copy.deepcopy(base_segments))
