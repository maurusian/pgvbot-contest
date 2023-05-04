import wikitextparser as wtp
import pywikibot, re
from datetime import datetime, timedelta

COMPETITION_START = datetime(2023, 4, 25, 0, 0)
COMPETITION_END = datetime(2023, 6, 10, 11, 59)

def remove_empty_lines(text: str) -> str:
    """
    Remove empty lines from a multiline string.

    :param text: A multiline string.
    :return: The input string with empty lines removed.
    """
    lines = text.splitlines()
    return [line for line in lines if line.strip()]

def user_modified_page_since(page: pywikibot.Page, username: str, date: datetime) -> bool:
    date_minus_one_hour = date - timedelta(hours=1)
    #starttime = max(date_minus_one_hour, COMPETITION_START)
    endtime = min(datetime.now(), COMPETITION_END)

    print("checking page revisions for:",page.title())
    #print(list(page.revisions(reverse=True)))
    #print(list(page.revisions(reverse=True, starttime=starttime, endtime=endtime)))
    
    for revision in page.revisions(reverse=True, starttime=COMPETITION_START, endtime=endtime):
        if revision["user"].lower() == username.lower():
            return True
    return False

def get_wikipedia_page(qcode: str, lang: str) -> pywikibot.Page:
    """
    Get the Wikipedia page for a language given the Wikidata Qcode.

    :param qcode: A string representing the Wikidata Qcode.
    :param lang: A string representing the language code.
    :return: A pywikibot.Page object if the page exists, None otherwise.
    """
    wikidata_site = pywikibot.Site('wikidata', 'wikidata')
    item = pywikibot.ItemPage(wikidata_site, qcode)
    
    try:
        item.get()
    except pywikibot.NoPage:
        return None

    sitelinks = item.sitelinks

    if f'{lang}wiki' in sitelinks:
        sitelink = sitelinks[f'{lang}wiki']
        page_title = sitelink.title
        site = pywikibot.Site(lang, 'wikipedia')
        page = pywikibot.Page(site, page_title)
        return page
    else:
        return None

def is_more_than_one_day_old(dt: datetime) -> bool:
    """
    Check if a datetime object is more than 1 day old.

    :param dt: A datetime object to be checked.
    :return: True if the datetime object is more than 1 day old, False otherwise.
    """
    now = datetime.now()
    one_day_ago = now - timedelta(days=1)
    return dt < one_day_ago


def get_section_contents(page):
    sections = {}
    wikitext = page.text

    main_sections = list(re.finditer(r'(==[^=]+==\n)', wikitext))

    # Remove the last main section
    main_sections = main_sections[:-1]

    for i, main_section in enumerate(main_sections):
        main_title = main_section.group().strip('= \n')
        main_start = main_section.end()
        main_end = main_sections[i + 1].start() if i + 1 < len(main_sections) else len(wikitext)
        main_content = wikitext[main_start:main_end]

        sub_sections = list(re.finditer(r'(===[^=]+===\n)', main_content))
        sub_sections.append(re.search(r'(==[^=]+==\n)', main_content))
        sub_sections = [s for s in sub_sections if s is not None]

        sub_content_dict = {}
        for j, sub_section in enumerate(sub_sections[:-1]):
            sub_title = sub_section.group().strip('= \n')
            sub_start = sub_section.end()
            sub_end = sub_sections[j + 1].start() if j + 1 < len(sub_sections) else len(main_content)
            sub_content = main_content[sub_start:sub_end].strip()

            sub_content_dict[sub_title] = sub_content

        sections[main_title] = sub_content_dict
    
    # Remove the last subsection of the last main section
    last_main_section = list(sections.keys())[-1]
    last_subsection = list(sections[last_main_section].keys())[-1]
    del sections[last_main_section][last_subsection]

    return sections

def get_section_by_title(text, sub_section_title):
    """
    Extract the full wiki code of a section whose title is contained in the parameter "sub_section_title".

    :param text: The wiki text to search for the section
    :type text: str
    :param sub_section_title: The title of the section to extract
    :type sub_section_title: str
    :return: The extracted section, or None if not found
    :rtype: str or None
    """
    # Create a regex pattern to match the section title at any level
    pattern = r'(^={2,} *' + re.escape(sub_section_title) + r' *={2,}\n)(.*?)(?=(?:\n={2,}[^=]+={2,})|\Z)'

    # Search for the section using the regex pattern
    match = re.search(pattern, text, flags=re.MULTILINE | re.DOTALL)

    # Return the section if found, or None if not found
    if match:
        return match.group(1) + match.group(2)
    else:
        return None

def parse_table(wikitext,index):
    table_pattern = r'\{\|.*?\|\}'
    table_match = re.findall(table_pattern, wikitext, flags=re.DOTALL)

    if len(table_match) >= 2:
        second_table = table_match[1]
        row_pattern = r'\|-\s*(.*?)\s*(?=\|-|\|\})'
        rows = re.findall(row_pattern, second_table, flags=re.DOTALL)

        usernames = []
        for row in rows:
            username_pattern = r'\{\{مس\|([^}]+)\}\}'
            username_match = re.search(username_pattern, row)
            if username_match:
                username = username_match.group(1).strip()
                usernames.append(username)

        return usernames
    else:
        print("Could not find the second table.")
        return None

def parse_wikipedia_table(wikitext: str, index) -> list:
    """
    Parse a Wikipedia table from wikitext and return a list of dictionaries.

    :param wikitext: A string containing the wikitext of a Wikipedia table.
    :return: A list of dictionaries, where each dictionary represents a row in the table with keys as the headers.
    """
    parsed_wikitext = wtp.parse(wikitext)
    table = parsed_wikitext.tables[index]
    data = table.data()

    #print(parsed_wikitext.tables)

    headers = data[0]
    rows = data[1:]

    table_data = []
    for row in rows:
        row_data = {}
        for index, header in enumerate(headers):
            row_data[header] = row[index].strip()
        table_data.append(row_data)

    return table_data


def list_of_dicts_to_wikitext_table(data: list) -> str:
    """
    Convert a list of dictionaries into a wikitext table with proper headers.

    :param data: A list of dictionaries, where each dictionary represents a row in the table with keys as the headers.
    :return: A string containing the wikitext of a Wikipedia table.
    """
    headers = list(data[0].keys())
    wikitext_table = '{| class="wikitable"\n|-\n'
    wikitext_table += ''.join(['! ' + header + '\n' for header in headers])

    for row in data:
        wikitext_table += '|-\n'
        wikitext_table += ''.join(['| ' + row[header] + '\n' for header in headers])

    wikitext_table += '|}'
    return wikitext_table

def extract_qcodes(table_data) -> list:
    """
    Extract the list of qcodes from the first column of each row.

    :param table_data: A list of lists, where each inner list represents a row in the table.
    :return: A list of qcodes extracted from the first column.
    """
    qcodes = []
    #print("table_data**************************")
    #print(table_data)
    qcode_match = re.findall(r'Q\d+', str(table_data))

    return list(set(qcode_match))
    

def find_row_by_qcode(table_data: list, qcode: str) -> str:
    """
    Find a row by Qcode and retrieve the value of the last column on that row.

    :param table_data: A list of lists, where each inner list represents a row in the table.
    :param qcode: A string representing the Qcode to search for.
    :return: The value of the last column on the row with the given Qcode.
    """
    for row in table_data:
        if qcode in row[1]:  # Search in the second column (index 1)
            return row[-1]  # Return the value of the last column
    return None

if __name__ == '__main__':
    site = pywikibot.Site("ar","wikipedia")
    title = "ويكيبيديا:مسابقة ويكيبيديا المغرب/المواضيع/سينما"
    page = pywikibot.Page(site,title)

    table_list = parse_wikipedia_table(page.text,0)

    for key, value in table_list[0].items():
        print('[['+key+']]..'+value)



              
