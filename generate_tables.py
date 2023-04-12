import json
import re
import pywikibot

def extract_section_title(wikicode):
    section_title_pattern = r'==\s*(.*?)\s*=='
    match = re.search(section_title_pattern, wikicode)
    return match.group(1) if match else None
    

def parse_qcodes(wikicode):
    missing_pattern = r'=== Missing ===\n[\t ]*\{\{#invoke:Missing articles\|table\|(.+?)\}\}'
    improve_pattern = r'=== To improve ===\n[\t ]*\{\{#invoke:Missing articles\|table\|(.+?)\}\}'
    
    missing_match = re.search(missing_pattern, wikicode)
    improve_match = re.search(improve_pattern, wikicode)

    missing_qcodes = missing_match.group(1).split('|') if missing_match else []
    print(missing_qcodes)
    improve_qcodes = improve_match.group(1).split('|') if improve_match else []

    return missing_qcodes, improve_qcodes

def generate_wikicode(lang, lang_data, wikicode):

    supported_langs = lang_data["supported_languages"]
    translations = lang_data["translations"]

    missing_qcodes, improve_qcodes = parse_qcodes(wikicode)

    if len(missing_qcodes) > 0 or len(improve_qcodes) > 0:
        
        template = f"""
    == {translations['sections'][extract_section_title(wikicode)]['section_title']} ==
    """
        if len(missing_qcodes) > 0:
            template +="""
    === {translations['missing_title']} ===
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
    lang = "ar"
    wikilangs = {"ar":"ary","ary":"ary","shi":"shi"}
    wikilang = wikilangs[lang]
    # Fetch the JSON data for the specified language project from the MediaWiki namespace
    site = pywikibot.Site(wikilang, 'wikipedia')
    json_page = pywikibot.Page(site, f'MediaWiki:{lang}_translation.json')
    print(json_page)
    lang_data = json.loads(json_page.text)

    input_wikicode = """
    == Scientists and engineers ==
    === Missing ===
    {{#invoke:Missing articles|table|Q16269639|Q1912377|Q113633472|Q27960245|Q6916980|Q3216750|Q3351852|Q3474820|Q3571308|Q3484194|Q6085012|Q8059061|Q99658775|Q106291673|Q3018520|Q60834907|Q28146571|Q109470767}}

    === To improve ===
{{#invoke:Missing articles|table|Q56949282|Q2827656|Q19951780|Q2821278|Q74289744|Q3318806|Q718239|Q16195662|Q4664587|Q3017491|Q6524517|Q59149378|Q2821198|Q3126605|Q108846334|Q2850109|Q2821128|Q108839644|Q65707471|Q65659104}}

    """

    generated_wikicode = generate_wikicode(lang, lang_data, input_wikicode)
    #print(generated_wikicode)

    site = pywikibot.Site(lang, 'wikipedia')
    page = pywikibot.Page(site, f"{lang_data['main_page']}/{lang_data['translations']['sections'][extract_section_title(input_wikicode)]['subpage']}")
    tmp = page.text
    if tmp  == "":
        tmp = generated_wikicode
    else:
        if section_title not in tmp:
            tmp+="\n\n"+generated_wikicode

    if tmp != page.text:
        page.text = tmp
        print(page.title())
        print(page.text)
        print(lang_data["save_message"])
        page.save(lang_data["save_message"])
