from pybtex.database.input import bibtex
import pybtex.database.input.bibtex 
from time import strptime
import string
import html
import os
import re
import sys

# Define publication types and their corresponding BibTeX entry types
pub_types = {
    "talks": {
        "entry_types": ["unpublished"],
        "venuekey": "eventtitle",
        "venue-pretext": "",
        "collection": {"name":"talks",
                        "permalink":"/talks/"}
    },
    "dataset": {
        "entry_types": ["dataset", "misc"],
        "venuekey": "publisher",
        "venue-pretext": "",
        "collection": {"name":"publications",
                        "permalink":"/publication/"}
    },
    "proceeding": {
        "entry_types": ["inproceedings", "conference"],
        "venuekey": "booktitle",
        "venue-pretext": "",
        "collection": {"name":"publications",
                        "permalink":"/publication/"}
    },
    "journal": {
        "entry_types": ["article"],
        "venuekey": "journaltitle",
        "venue-pretext": "",
        "collection": {"name":"publications",
                        "permalink":"/publication/"}
    },
    "online": {
        "entry_types": ["online"],
        "venuekey": "organization",
        "venue-pretext": "",
        "collection": {"name":"publications",
                        "permalink":"/publication/"}
    }
}

# Single BibTeX file for all publication types
bib_file = "markdown_generator/lw_publications_04_2025.bib"

html_escape_table = {
    "&": "&amp;",
    '"': "&quot;",
    "'": "&apos;"
    }

def html_escape(text):
    """Produce entities within text."""
    return "".join(html_escape_table.get(c,c) for c in text)

# Create necessary directories
for pub_type in pub_types.values():
    dir_path = f"../_{pub_type['collection']['name']}"
    os.makedirs(dir_path, exist_ok=True)
    print(f"Created directory: {dir_path}")

# Custom parser to handle duplicate entries
class CustomBibTeXParser(bibtex.Parser):
    def __init__(self):
        super().__init__()
        self.entry_count = {}
    
    def process_entry(self, entry_type, key, fields):
        # If key already exists, append a counter to make it unique
        if key in self.entry_count:
            self.entry_count[key] += 1
            new_key = f"{key}_{self.entry_count[key]}"
            print(f"WARNING: Duplicate entry key '{key}' found. Using '{new_key}' instead.")
            key = new_key
        else:
            self.entry_count[key] = 0
        
        # Call the parent method with the potentially modified key
        super().process_entry(entry_type, key, fields)

# Use the custom parser
parser = CustomBibTeXParser()

try:
    bibdata = parser.parse_file(bib_file)
except Exception as e:
    print(f"Error parsing BibTeX file: {e}")
    sys.exit(1)

# Get the absolute path to the script's directory
script_dir = os.path.dirname(os.path.abspath(__file__))
# Get the absolute path to the parent directory (where _publications and _talks folders are)
parent_dir = os.path.dirname(script_dir)

#loop through the individual references in a given bibtex file
for bib_id in bibdata.entries:
    #reset default date
    pub_year = "1900"
    pub_month = "01"
    pub_day = "01"
    
    b = bibdata.entries[bib_id].fields
    entry_type = bibdata.entries[bib_id].type.lower()
    
    # Determine publication type based on entry type
    pub_type = None
    for type_name, type_info in pub_types.items():
        if entry_type in type_info["entry_types"]:
            pub_type = type_name
            break
    
    # If no matching type found, default to journal
    if pub_type is None:
        pub_type = "journal"
    
    try:
        try:
            pub_year = f'{b["year"]}'

            #todo: this hack for month and day needs some cleanup
            if "month" in b.keys(): 
                if(len(b["month"])<3):
                    pub_month = "0"+b["month"]
                    pub_month = pub_month[-2:]
                elif(b["month"] not in range(12)):
                    tmnth = strptime(b["month"][:3],'%b').tm_mon   
                    pub_month = "{:02d}".format(tmnth) 
                else:
                    pub_month = str(b["month"])
            if "day" in b.keys(): 
                pub_day = str(b["day"])

            pub_date = pub_year+"-"+pub_month+"-"+pub_day
        except:
            pub_date = f'{b["date"]}'
                
        
        #strip out {} as needed (some bibtex entries that maintain formatting)
        clean_title = b["title"].replace("{", "").replace("}","").replace("\\","").replace(" ","-")    

        url_slug = re.sub("\\[.*\\]|[^a-zA-Z0-9_-]", "", clean_title)
        url_slug = url_slug.replace("--","-")

        md_filename = (str(pub_date) + "-" + url_slug + ".md").replace("--","-")
        html_filename = (str(pub_date) + "-" + url_slug).replace("--","-")

        #Build Citation from text
        citation = ""

        #citation authors - todo - add highlighting for primary author?
        for author in bibdata.entries[bib_id].persons["author"]:
            citation = citation+" "+author.first_names[0]+" "+author.last_names[0]+", "

        #citation title
        citation = citation + "\"" + html_escape(b["title"].replace("{", "").replace("}","").replace("\\","")) + ".\""

        #add venue logic depending on citation type
        venue = pub_types[pub_type]["venue-pretext"]+b[pub_types[pub_type]["venuekey"]].replace("{", "").replace("}","").replace("\\","").replace(",","")

        citation = citation + " " + html_escape(venue)
        citation = citation + ", " + pub_year + "."

        
        ## YAML variables
        md = "---\ntitle: \""   + html_escape(b["title"].replace("{", "").replace("}","").replace("\\","")) + '\"\n'
        
        md += """collection: """ +  pub_types[pub_type]["collection"]["name"]

        md += """\npermalink: """ + pub_types[pub_type]["collection"]["permalink"]  + html_filename
        
        note = False
        if "note" in b.keys():
            if len(str(b["note"])) > 5:
                md += "\nexcerpt: '" + html_escape(b["note"]) + "'"
                note = True

        md += "\ndate: " + str(pub_date) 

        md += "\nvenue: '" + html_escape(venue) + "'"
        
        url = False
        if "url" in b.keys():
            if len(str(b["url"])) > 5:
                md += "\npaperurl: '" + b["url"] + "'"
                url = True

        md += "\ncitation: '" + html_escape(citation) + "'"

        # doi for all publications with doi
        try:
            md += "\ndoi: '" + b["doi"] + "'"
        except:
            try:
                if "url" in b.keys() and len(str(b["url"])) > 5:
                    md += "\ndoi: '" + b["url"] + "'"
            except:
                pass
        
        md += "\n---"

        
        ## Markdown description for individual page
        if note:
            md += "\n" + html_escape(b["note"]) + "\n"

        md_filename = os.path.basename(md_filename)

        # Construct the absolute path to the output directory
        output_dir = os.path.join(parent_dir, f"_{pub_types[pub_type]['collection']['name']}")
        # Construct the absolute path to the output file
        output_path = os.path.join(output_dir, md_filename)
        
        # Ensure the output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Write the file
        with open(output_path, 'w', encoding="utf-8") as f:
            f.write(md)
        print(f'SUCESSFULLY PARSED {bib_id}: \"', b["title"][:60],"..."*(len(b['title'])>60),"\"")
        print(f'  Written to: {output_path}')
    # field may not exist for a reference
    except KeyError as e:
        print(f'WARNING Missing Expected Field {e} from entry {bib_id}: \"', b["title"][:30],"..."*(len(b['title'])>30),"\"")
        continue 