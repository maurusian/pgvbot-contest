import wikitextparser as wtp
import pywikibot, re

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

    print(parsed_wikitext.tables)

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

if __name__ == '__main__':
    site = pywikibot.Site("ar","wikipedia")
    title = "ويكيبيديا:مسابقة ويكيبيديا المغرب/المشاركون"
    page = pywikibot.Page(site,title)

    table_list = parse_wikipedia_table(page.text)

    for key, value in table_list[0].items():
        print('[['+key+']]..'+value)
              
