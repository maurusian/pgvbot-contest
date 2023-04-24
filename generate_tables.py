import json
import re
import pywikibot

def get_main_sections(text):
    sections = re.split(r'(^==[^=]+==\n)', text, flags=re.MULTILINE)
    main_sections = []
    for i in range(1, len(sections), 2):
        main_sections.append(sections[i] + sections[i + 1])
    return main_sections

def get_subpages(site, page_title):
    prefix = page_title + '/'
    subpages = []
    for page in pywikibot.Page(pywikibot.Link(prefix, site)).getReferences(follow_redirects=False):
        if page.title().startswith(prefix):
            subpages.append(page)
    return subpages

def get_sections_from_page_and_subpages(site, page_title):
    page = pywikibot.Page(site, page_title)
    main_sections = get_main_sections(page.text)
    subpages = get_subpages(site, page_title)

    for subpage in subpages:
        main_sections += get_main_sections(subpage.text)

    return main_sections

def extract_section_title(wikicode):
    section_title_pattern = r'==\s*(.*?)\s*=='
    match = re.search(section_title_pattern, wikicode)
    return match.group(1) if match else None
    

def parse_qcodes(wikicode):
    missing_pattern = r'=== Missing ===[\n]+[\t ]*\{\{#invoke:Missing articles\|table\|(.+?)\}\}'
    improve_pattern = r'=== To improve ===[\n]+[\t ]*\{\{#invoke:Missing articles\|table\|(.+?)\}\}'
    
    missing_match = re.search(missing_pattern, wikicode)
    improve_match = re.search(improve_pattern, wikicode)

    missing_qcodes = missing_match.group(1).split('|') if missing_match else []
    #print(missing_qcodes)
    improve_qcodes = improve_match.group(1).split('|') if improve_match else []

    return missing_qcodes, improve_qcodes

def generate_wikicode(lang, lang_data, wikicode):

    supported_langs = lang_data["supported_languages"]
    translations = lang_data["translations"]

    '''only for debugging
    print(translations['missing_title'])
    print(translations['sections'][extract_section_title(wikicode)]['section_title'])
    print(translations['row_number'])
    print(translations['topic'])
    '''
    
    missing_qcodes, improve_qcodes = parse_qcodes(wikicode)

    if len(missing_qcodes) > 0 or len(improve_qcodes) > 0:
        
        template = f"""== {translations['sections'][extract_section_title(wikicode)]['section_title']} ==
"""
        if len(missing_qcodes) > 0:
            template +=f"""=== {translations['missing_title']} ===
{{| class="wikitable"
! {translations["row_number"]}\n! {translations['topic']}\n
"""
        
            for supported_lang in supported_langs:
                template += f"! {translations[supported_lang]}\n"
            template += f"! {translations['reservation_status']}\n"

            # Missing section
            for idx, qcode in enumerate(missing_qcodes):
                #wikidata_link_tmp = translations['Wikidata_link_template']
                template += f"|-\n| {idx + 1}\n| {{{{{translations['Wikidata_link_template']}|{qcode}}}}}\n"
                for lang in supported_langs:
                    template += f"| {{{{#invoke:Sitelink|getSitelink2|{qcode}|{lang}}}}}\n"
                template += "| \n"
            template += "|}\n"
        if len(improve_qcodes) > 0:
            # To improve section
            template += f"=== {translations['improve_title']} ===\n{{| class=\"wikitable\"\n! {translations['row_number']}\n! {translations['topic']}\n"
            for lang in supported_langs:
                template += f"! {translations[lang]}\n"
            template += f"! {translations['reservation_status']}\n"

            for idx, qcode in enumerate(improve_qcodes):
                template += f"|-\n| {idx + 1}\n| {{{{{translations['Wikidata_link_template']}|{qcode}}}}}\n"
                for lang in supported_langs:
                    template += f"| {{{{#invoke:Sitelink|getSitelink2|{qcode}|{lang}}}}}\n"
                template += "| \n"

            template += "|}"
    else:
        template = ""
        print("no values received from tables")

    return template


if __name__=='__main__':

    lang = "shi"
    
    metapage_title = f"User:Ideophagous/test/{lang}"

    meta_site = pywikibot.Site('meta', 'meta')

    wikilangs = {"ar":"ary","ary":"ary","shi":"shi"}

    wikilang = wikilangs[lang]
    # Fetch the JSON data for the specified language project from the MediaWiki namespace
    site = pywikibot.Site(wikilang, 'wikipedia')
    json_page = pywikibot.Page(site, f'MediaWiki:{lang}_translation.json')
    #print(json_page)
    lang_data = json.loads(json_page.text)

    sections = get_sections_from_page_and_subpages(meta_site, metapage_title)

    for section in sections:

        generated_wikicode = generate_wikicode(lang, lang_data, section)
        #print(generated_wikicode)

        site = pywikibot.Site(wikilang, 'wikipedia')
        section_title = extract_section_title(section)
        title = f"{lang_data['main_page']}/{lang_data['translations']['sections'][section_title]['subpage']}"
        page = pywikibot.Page(site, title)
        tmp = page.text
        if tmp  == "":
            tmp = generated_wikicode
        else:
            if section_title not in tmp:
                tmp+="\n\n"+generated_wikicode
        
        footer = f"{lang_data['reservation_section']}"

        if footer not in tmp:
            tmp+='\n\n'+footer
        else:
            tmp = tmp.replace(footer,"")
            tmp+='\n\n'+footer #keep footer at the bottom
        if tmp != page.text:
            '''only for debugging
            print(tmp)
            print(page.title())
            print(page.text)
            print(lang_data["save_message"])
            break
            '''
            page.text = tmp
            page.save(lang_data["save_message"])

