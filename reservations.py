import pywikibot, json, re, sys, ast
from datetime import datetime, timedelta
import help_functions as hf
import ipaddress

JSON_SITE_LANG = {"ar":"ary","ary":"ary","shi":"shi"}


def is_ip_address(username):
    try:
        ipaddress.ip_address(username)
        return True
    except ValueError:
        return False

def read_json_file(site, json_page_title):
    json_page = pywikibot.Page(site, json_page_title)
    json_content = json_page.get()
    return json.loads(json_content)

# Function to extract the user name(s) from the line
def get_user_names_from_line(line, unsigned_template_name, user_namespace):
    user_names = re.findall(r'\[\[(?:' + re.escape(user_namespace) + r'|User):([^|\]]+)\|', line, flags=re.IGNORECASE)
    #print(user_names)
    if not user_names:
        unsigned_match = re.search(r'{{' + re.escape(unsigned_template_name) + r'\|1=([^|}]+)', line)
        if unsigned_match:
            user_names.append(unsigned_match.group(1))

        if user_names:
            return list(set(user_names))
    else:
        return list(set(user_names))
    
    return None

# Function to extract the date from the line
def get_date_from_line(line, month_names):
    # Replace placeholders with actual month names in the date regex pattern
    month_names_pattern = '|'.join(month_names)
    date_pattern = r'(\d{1,2}):(\d{2})، (\d{1,2}) (' + month_names_pattern + r') (\d{4})'
    
    match = re.search(date_pattern, line)
    if match:
        hour, minute, day, month_name, year = match.groups()
        month = month_names.index(month_name) + 1
        return datetime(int(year), month, int(day), int(hour), int(minute))
    else:
        return None

# Function to extract the reserved topics (Qcodes) as a list
def get_reserved_topics_from_line(line):
    qcodes = re.findall(r'\b(q\d+)\b', line, flags=re.IGNORECASE)
    return [qcode.upper() for qcode in qcodes]


def write_notifications(site,notification_list,notification_page_title,save_message):
    notification_page = pywikibot.Page(site,notification_page_title)
    temp = notification_page.text
    for notification in notification_list:
        if notification not in temp:
            temp.text += '\n*'+notification+'--~~~~'

    if temp != notification_page.text:
        notification_page.text = temp
        notification_page.save(save_message)

def load_participants(site,json_data):
    username_pattern = r'\{\{مس\|([^}]+)\}\}'
    participants_page_title = f"{json_data['pages']['main_page']}/{json_data['pages']['participants_page']}"
    participants_page = pywikibot.Page(site,participants_page_title)
    
    usernames = re.findall(username_pattern, participants_page.text)

    # Filter out any non-matching usernames, like "-"
    filtered_usernames = [username for username in usernames if username != '-']

    return filtered_usernames

def process_raw_reservations(site,json_data):
    reservation_section_title = f"{json_data['reservation_section_title']}"
    raw_reservations = {'user_reservations':{},'anonymous_reservations':{},'unsigned_reservations':{}}
    pretreated_raw_reservations = {'user_reservations':{},'anonymous_reservations':{}}
    discarded_lines = []
    main_topic_page_title = f"{json_data['pages']['main_page']}/{json_data['pages']['topics']['main_topic_page']}"

    unsigned_template_name = json_data['translations']['templates']['unsigned_template']
    user_namespace = json_data['translations']['namespaces']['user']
    
    for subpage_title in json_data['pages']['topics']['subpages']:
        topic_page = pywikibot.Page(site,f"{main_topic_page_title}/{subpage_title}")
        #print(topic_page.title())
        #print(subpage_title)
        #print(reservation_section_title)
        reservation_section = hf.get_section_by_title(topic_page.text, reservation_section_title)
        #print(reservation_section)
        if reservation_section is not None:
            reservation_lines = hf.remove_empty_lines(reservation_section)
            for line in reservation_lines:
                if line.strip() != "" and line.strip() != "=== قائمة الحجز ===":
                    usernames = get_user_names_from_line(line, unsigned_template_name, user_namespace)
                        
                    jury = json_data['jury']
                    organizers = json_data['organizers']
                    bot = json_data['bot']
                    if usernames is not None:
                        if len(usernames) == 1:
                            username = usernames[0]
                        elif usernames[-1] in jury or usernames[-1] in organizers:
                            username = usernames[-1]
                        else:
                            username = usernames[0]
                        if username not in jury and username not in organizers and username != bot:
                        
                            line_index = reservation_lines.index(line)
                            ignore_line = False
                            next_line = None
                            if line_index < len(reservation_lines)-1:
                                next_line = reservation_lines[line_index+1]
                                next_usernames = get_user_names_from_line(next_line, unsigned_template_name, user_namespace)
                                #print(username)
                                #print(next_username)
                                if next_usernames is not None:
                                    if len(next_usernames) == 1:
                                        next_username = next_usernames[0]
                                    elif next_usernames[-1] in jury or next_usernames[-1] in organizers or next_username == bot:
                                        next_username = next_usernames[-1]
                                    else:
                                        next_username = next_usernames[0]
                                    if next_username in jury or next_username in organizers or next_username == bot:
                                        
                                        ignore_line = True
                            if not ignore_line:
                                #print(username)
                                month_names = json_data['months']
                                date = get_date_from_line(line,month_names)
                                #print(date)
                                reserved_topics = get_reserved_topics_from_line(line)
                                #print(reserved_topics)
                                if '/' in username:
                                    username = username.split('/')[-1]
                                if is_ip_address(username):
                                    if username not in raw_reservations['anonymous_reservations'].keys():
                                        raw_reservations['anonymous_reservations'][username] = {subpage_title:[{'reservation':line,'answer':f"{json_data['reservation_answers']['no_anonymous']}"}]}
                                    else:
                                        if subpage_title not in raw_reservations['anonymous_reservations'][username].keys():
                                            raw_reservations['anonymous_reservations'][username][subpage_title] = [{'reservation':line,'answer':f"{json_data['reservation_answers']['no_anonymous']}"}]
                                        else:
                                            raw_reservations['anonymous_reserations'][username][subpage_title].append({'reservation':line,'answer':f"{json_data['reservation_answers']['no_anonymous']}"})
                                else:
                                    if username not in raw_reservations['user_reservations'].keys():
                                        raw_reservations['user_reservations'][username] = {subpage_title:[{'reservation':line,'reserved_topics':reserved_topics,'date':date}]}
                                    else:
                                        if subpage_title not in raw_reservations['user_reservations'][username].keys():
                                            raw_reservations['user_reservations'][username][subpage_title] = [{'reservation':line,'reserved_topics':reserved_topics,'date':date}]
                                        else:
                                            raw_reservations['user_reservations'][username][subpage_title].append({'reservation':line,'reserved_topics':reserved_topics,'date':date})
                            else:

                                #ignored reservation must still be checked if they were added to the table or not, or if they should be removed, depending on the response
                                #month_names = json_data['months']
                                #date = get_date_from_line(line,month_names)
                                reserved_topics = get_reserved_topics_from_line(line)
                                if '/' in username:
                                    username = username.split('/')[-1]
                                if is_ip_address(username):
                                    if username not in pretreated_raw_reservations['anonymous_reservations'].keys():
                                        pretreated_raw_reservations['anonymous_reservations'][username] = {subpage_title:[{'reservation':line,'next_line':next_line,'reserved_topics':reserved_topics}]}
                                    else:
                                        if subpage_title not in pretreated_raw_reservations['anonymous_reservations'][username].keys():
                                            pretreated_raw_reservations['anonymous_reservations'][username][subpage_title] = [{'reservation':line,'next_line':next_line,'reserved_topics':reserved_topics}]
                                        else:
                                            pretreated_raw_reservations['anonymous_reserations'][username][subpage_title].append({'reservation':line,'next_line':next_line,'reserved_topics':reserved_topics})
                                else:
                                    if username not in pretreated_raw_reservations['user_reservations'].keys():
                                        pretreated_raw_reservations['user_reservations'][username] = {subpage_title:[{'reservation':line,'next_line':next_line,'reserved_topics':reserved_topics}]}
                                    else:
                                        if subpage_title not in pretreated_raw_reservations['user_reservations'][username].keys():
                                            pretreated_raw_reservations['user_reservations'][username][subpage_title] = [{'reservation':line,'next_line':next_line,'reserved_topics':reserved_topics}]
                                        else:
                                            pretreated_raw_reservations['user_reservations'][username][subpage_title].append({'reservation':line,'next_line':next_line,'reserved_topics':reserved_topics})
                            
                    elif username not in jury and username not in organizers and username != bot:
                        #treat untreated unsigned reservations, treated unsigned reservations (followed by a response from an organizer or jury member are completely ignored)
                        line_index = reservation_lines.index(line)
                        ignore_line = False
                        next_line = None
                        if line_index < len(reservation_lines)-1:
                            next_line = reservation_lines[line_index+1]
                            next_username = get_user_names_from_line(next_line, unsigned_template_name, user_namespace)
                            #print(username)
                            #print(next_username)
                                
                            if next_usernames is not None:
                                if len(next_usernames) == 1:
                                    next_username = next_usernames[0]
                                elif next_usernames[-1] in jury or next_usernames[-1] in organizers:
                                    next_username = next_usernames[-1]
                                else:
                                    next_username = next_usernames[0]
                                if next_username in jury or next_username in organizers or next_username == bot:
                                            
                                    ignore_line = True
                                
                        if not ignore_line:
                            reserved_topics = get_reserved_topics_from_line(line)
                            if reserved_topics is not None and len(reserved_topics)>0:
                                if subpage_title not in raw_reservations['unsigned_reservations'].keys():
                                    raw_reservations['unsigned_reservations'][subpage_title] = [line]
                                else:
                                    raw_reservations['unsigned_reservations'][subpage_title].append(line)
                            else:
                                #lines that do not contain any clearly relevant information
                                discarded_lines.append(line)
                        
    return raw_reservations, pretreated_raw_reservations, discarded_lines




def get_topic_qcodes(site,topics_tables):
    return hf.extract_qcodes(topics_tables)

def convert_topics_tables_to_dicts(topics_tables,json_data):
    dictionarized_topics_tables = topics_tables
    qcode_dict = {}
    for topic, section in topics_tables.items():
        #print(topic)
        for section_title, content in section.items():
            #print(section_title)
            for subsection_title, subsection_content in content.items():
                #print(subsection_title)
                new_topic_table = hf.parse_wikipedia_table(subsection_content,0)
                dictionarized_topics_tables[topic][section_title][subsection_title] = new_topic_table
                for i in range(len(new_topic_table)):
                    qcode = hf.extract_qcodes(new_topic_table[i][json_data["translations"]["topic"]])[0]
                    if qcode not in new_topic_table[i].keys():
                        rownum = i
                        qcode_dict[qcode] = [{"topic":topic
                                              ,"section_title":section_title
                                              ,"subsection_title":subsection_title
                                              ,"rownum":rownum
                                              ,"reservation":new_topic_table[i][json_data["translations"]["reservation_status"]]}]
                    else:
                        qcode_dict[qcode].append({"topic":topic
                                                  ,"section_title":section_title
                                                  ,"subsection_title":subsection_title
                                                  ,"rownum":rownum
                                                  ,"reservation":new_topic_table[i][json_data["translations"]["reservation_status"]]})
                    
                #print(type(dictionarized_topics_tables[topic][section_title][subsection_title][0]))

    return dictionarized_topics_tables, qcode_dict


def process_table_reservations():
    pass
        

def load_topics_tables(site,json_data):
    main_page = f"{json_data['pages']['main_page']}"
    #print(main_page)
    main_topic_page = f"{main_page}/{json_data['pages']['topics']['main_topic_page']}"
    #print(main_topic_page)
    topic_subpage_names = ast.literal_eval(f"{json_data['pages']['topics']['subpages']}")
    #print(topic_subpage_names)
    topics_tables_dict = {}
    for subpage_name in topic_subpage_names:
        subpage_ttl = f"{main_topic_page}/{subpage_name}"
        #print(subpage_ttl)
        subpage = pywikibot.Page(site,subpage_ttl)
        topics_tables_dict[subpage_name] = hf.get_section_contents(subpage)

    return topics_tables_dict


def write_to_notification_page(notifications,notifications_page,json_data):
    SAVE_MESSAGE = f"{json_data['SAVE_MESSAGES_DICT']['NOTIFY']}"
    try:
        notifications_page.text+='\n'+notifications
        notifications_page.save(SAVE_MESSAGE)
    except:
        print("Could not save to notification page.")
        print(sys.exc_info())

def process_answers(answers,json_data):
    #print("answers len:",len(answers.values()))
    if len(set(answers.values())) == 1:
        if list(answers.values())[0] == "accepted":
            return json_data['reservation_answers']['accepted_reservation']
        elif list(answers.values())[0] == "expired":
            return json_data['reservation_answers']['cancel_reservation_not_modified']
        elif list(answers.values())[0] == "inexistent":
            return json_data['reservation_answers']['cancel_inexistent_topic']
        else:
            print("UNKNOWN response type")

    AND = f" {json_data['translations']['AND']} "
    return (json_data['reservation_answers']['mixed_answer']
        .replace("{rejected}", AND.join([key for key, value in answers.items() if value == "expired" or value == "inexistent"]))
        .replace("{accepted}", AND.join([key for key, value in answers.items() if value == "accepted"])))

def is_not_valid_participant(user,participants,jury,organizers,bot):
    lower_participants = [participant.lower() for participant in participants]
    lower_organizers = [organizer.lower() for organizer in organizers]
    lower_jury = [member.lower() for member in jury]
    lower_bot = bot.lower()

    lower_user = user.lower()

    return (lower_user not in lower_participants and lower_user not in lower_jury and lower_user not in lower_organizers and lower_user != lower_bot)

def get_user_reservations_from_table(dictionarized_topics_tables,json_data):
    raw_table_reservations = {"user_reservations":{},"anonymous_reservations":{},"improper_reservations":[]}

    topic_colname = json_data['translations']['topic']
    #print(topic_colname)
    resrv_colname = json_data['translations']['reservation_status']

    unsigned_template_name = json_data['translations']['templates']['unsigned_template']
    user_namespace = json_data['translations']['namespaces']['user']

    for topic, section in topics_tables.items():
        #print(topic)
        for section_title, content in section.items():
            #print(section_title)
            for subsection_title, table in content.items():
                #print(table[0].keys())
                for i in range(len(table)):
                    #print(topic, section_title, subsection_title, i)
                    
                    if table[i][resrv_colname].strip() != "":
                        usernames = get_user_names_from_line(table[i][resrv_colname], unsigned_template_name, user_namespace)
                        if usernames is None or len(usernames) == 0:
                            #add to improper / No username
                            raw_table_reservations["improper_reservations"].append({"topic":topic,"section_title":section_title
                                                                                    ,"subsection_title":subsection_title
                                                                                    ,"rownum":i
                                                                                    ,"reservation_line":table[i][resrv_colname].strip()
                                                                                    ,"reason":"nouser"
                                                                                    ,"reserved_code":get_reserved_topics_from_line(table[i][topic_colname])[0]})
                        elif len(usernames)>1:
                            raw_table_reservations["improper_reservations"].append({"topic":topic,"section_title":section_title
                                                                                    ,"subsection_title":subsection_title
                                                                                    ,"rownum":i
                                                                                    ,"reservation_line":table[i][resrv_colname].strip()
                                                                                    ,"reason":"multiple"
                                                                                    ,"reserved_code":get_reserved_topics_from_line(table[i][topic_colname])[0]})
                        else:
                            #further checks
                            username = usernames[0]
                            if '/' in username:
                                username = username.split('/')[-1]
                            if is_ip_address(username):
                                if username in raw_table_reservations["anonymous_reservations"].keys():
                                    
                                    raw_table_reservations["anonymous_reservations"][username].append({"topic":topic,"section_title":section_title
                                                                                    ,"subsection_title":subsection_title
                                                                                    ,"rownum":i
                                                                                    ,"reservation_line":table[i][resrv_colname]
                                                                                    ,"reserved_code":get_reserved_topics_from_line(table[i][topic_colname])[0]})
                                else:
                                    raw_table_reservations["anonymous_reservations"][username] = [{"topic":topic
                                                                                                ,"section_title":section_title
                                                                                                ,"subsection_title":subsection_title
                                                                                                ,"rownum":i
                                                                                                ,"reservation_line":table[i][resrv_colname].strip()
                                                                                                ,"reserved_code":get_reserved_topics_from_line(table[i][topic_colname])[0]}]
                            else:
                                #get date
                                month_names = json_data['months']
                                date = get_date_from_line(table[i][resrv_colname],month_names)
                                if date is not None:
                                    if username in raw_table_reservations["user_reservations"].keys():
                                        
                                        raw_table_reservations["user_reservations"][username].append({"topic":topic,"section_title":section_title
                                                                                        ,"subsection_title":subsection_title,"rownum":i
                                                                                        ,"reservation_line":table[i][resrv_colname].strip()
                                                                                        ,'date':date
                                                                                        ,"reserved_code":get_reserved_topics_from_line(table[i][topic_colname])[0]})
                                    else:
                                        raw_table_reservations["user_reservations"][username] = [{"topic":topic,"section_title":section_title
                                                                                        ,"subsection_title":subsection_title,"rownum":i
                                                                                        ,"reservation_line":table[i][resrv_colname].strip()
                                                                                        ,'date':date
                                                                                        ,"reserved_code":get_reserved_topics_from_line(table[i][topic_colname])[0]}]
                                else:
                                    raw_table_reservations["improper_reservations"].append({"topic":topic,"section_title":section_title
                                                                                    ,"subsection_title":subsection_title
                                                                                    ,"rownum":i
                                                                                    ,"reservation_line":table[i][resrv_colname].strip()
                                                                                    ,"reason":"nodate"
                                                                                    ,"reserved_code":get_reserved_topics_from_line(table[i][topic_colname])[0]})

    return raw_table_reservations


def get_inline_reservation_line_from_table_reservation(table_reservation_line,qcode,json_data):
    underway_template = "{{"+f"{json_data['translations']['templates']['underway_template']}"+"}}"
    completed_template = "{{"+f"{json_data['translations']['templates']['completed_template']}"+"}}"
    contrib_size_template = f"{json_data['translations']['templates']['contrib_size_template']}"
    inline_reservation_line = table_reservation_line.replace(underway_template,"").replace(completed_template,"")
    inline_reservation_line = re.sub(r'\{\{'+contrib_size_template+'\|[^{}]*\}\}', '', inline_reservation_line)

    return f"({qcode}) {inline_reservation_line}"
    
# Main section
if __name__ == "__main__":

    #set variables
    lang = "ar"
    site = pywikibot.Site(lang,"wikipedia")
    json_page_title = f"Mediawiki:{lang}_translation.json"
    json_data = read_json_file(pywikibot.Site(JSON_SITE_LANG[lang],"wikipedia"), json_page_title)
    jury = json_data['jury']
    organizers = json_data['organizers']
    bot = json_data['bot']
    notifications = json_data['notifications']
    unsigned_template_name = json_data['translations']['templates']['unsigned_template']
    user_namespace = json_data['translations']['namespaces']['user']

    resrv_colname = json_data['translations']['reservation_status']

    # Fetch the participant list   
    participants = load_participants(site,json_data)

    #fetch the topic tables raw with their wiki code
    topics_tables = load_topics_tables(site,json_data)
    #transform raw wikicode to a list of rows, each represented by a dictionary (overall same struct as topics_tables)
    #create a dictionary that contains the topics as keys, for easier access (instead of looping through the table structs
    #several times to find the same information
    dictionarized_topics_tables, qcode_dict = convert_topics_tables_to_dicts(topics_tables,json_data)

    '''
    topic = "تاريخ"
    section_title = "أحداث تاريخية"
    subsection_title = "غير موجود"

    for i in range(len(dictionarized_topics_tables[topic][section_title][subsection_title])):
        qcode = hf.extract_qcodes(dictionarized_topics_tables[topic][section_title][subsection_title][i][json_data["translations"]["topic"]])[0]
        print(i, dictionarized_topics_tables[topic][section_title][subsection_title][i]["الموضوع"])
        print(qcode_dict[qcode][0]["rownum"],qcode)

    #dictionarized_topics_tables[topic][section_title][subsection_title][rownum]

    
    #make sure no qcodes are repeated
    for qcode, content in qcode_dict.items():
        #print(qcode, len(content))
        if len(content)>1:
            print(qcode, content)
    '''

    #fetch the user reservations from the tables
    raw_table_reservations = get_user_reservations_from_table(dictionarized_topics_tables,json_data)

    #fetch inline reservations
    #dictionary key = user, value = list of qcodes of reserved topics
    raw_reservations, pretreated_raw_reservations, discarded_lines = process_raw_reservations(site,json_data)

    #run checks and add to notification list
    
    notification_list = []
    notifications_page_title = f"{json_data['pages']['main_page']}/{json_data['pages']['notifications_page']}"
    #print(notifications_page_title)
    notifications_page = pywikibot.Page(site,notifications_page_title)

    rewrite_table = False

    #validate reservations inline
    print("reservations inline")
    for user, reservations in raw_reservations["user_reservations"].items():
        if is_not_valid_participant(user,participants,jury,organizers,bot):
            print(user)
            subpage_title = list(reservations.keys())[0]
            subpage_link = f"{json_data['pages']['main_page']}/{json_data['pages']['topics']['main_topic_page']}/{subpage_title}"
            formatted_user_str = "{{"+f"{json_data['translations']['templates']['user_template']}|{user}{json_data['translations']['templates']['optional_user_template_param']}"+"}}"
            new_notification = f"{notifications['USER_NOT_REGISTERED']}".format(user=formatted_user_str, subpage_link=subpage_link, subpage_title=subpage_title)
            if new_notification[:-4] not in notifications_page.text:
                notification_list.append(new_notification)

        else:
            for subpage_title, topic_reservations in reservations.items():
                print(subpage_title)
                answers = {}
                for topic_reservation in topic_reservations:
                    if hf.is_more_than_one_day_old(topic_reservation['date']):
                        #check if each reserved topic has been modified by the user in the alloted time
                        reserved_topics = topic_reservation['reserved_topics']
                        for qcode in reserved_topics:
                            if qcode not in qcode_dict.keys():
                                answers[qcode] = "inexistent"
                            else:
                                page = hf.get_wikipedia_page(qcode, lang)

                                if page is None:
                                    
                                    print(f"page for language {lang} with qcode {qcode} doesn't exist!")
                                    #cancel reservation
                                    answers[qcode] = "expired"
                                    
                                    #remove reservation from table if already there

                                    topic = qcode_dict[qcode][0]["topic"]
                                    section_title = qcode_dict[qcode][0]["section_title"]
                                    subsection_title = qcode_dict[qcode][0]["subsection_title"]
                                    rownum = qcode_dict[qcode][0]["rownum"]
                                    table_reservation_line = dictionarized_topics_tables[topic][section_title][subsection_title][rownum][resrv_colname]
                                    if table_reservation_line != "":
                                        #check for conflict
                                        print(table_reservation_line)
                                        table_reserving_users = get_user_names_from_line(table_reservation_line, unsigned_template_name, user_namespace)
                                        #dictionarized_topics_tables[topic][section_title][subsection_title][rownum][resrv_colname] = topic_reservation['reservation']
                                        if table_reserving_users is not None:
                                            if table_reserving_users[0] != user:
                                                subpage_link = f"{json_data['pages']['main_page']}/{json_data['pages']['topics']['main_topic_page']}/{subpage_title}"
                                                notification = f"{notifications['RESERVATION_CONFLICT']}".format(qcode=qcode, page=subpage_link, subpage_title=subpage_title)
                                                notification_list.append(notification)
                                        else:
                                            dictionarized_topics_tables[topic][section_title][subsection_title][rownum][resrv_colname] = ""
                                            rewrite_table = True
                                elif hf.user_modified_page_since(page, user, topic_reservation['date']):
                                    #copy to table(s) if not already done
                                    #but first check if there's no conflict reservation in table by another participant
                                    """
                                    for x in range(len(qcode_dict[qcode])):
                                        qcode_reservation = qcode_dict[qcode][x]["reservation"]
                                    """
                                    #approve reservation in-line
                                    answers[qcode] = "accepted"

                                    #copy to dictionarized_topics_tables

                                    topic = qcode_dict[qcode][0]["topic"]
                                    section_title = qcode_dict[qcode][0]["section_title"]
                                    subsection_title = qcode_dict[qcode][0]["subsection_title"]
                                    rownum = qcode_dict[qcode][0]["rownum"]
                                    table_reservation_line = dictionarized_topics_tables[topic][section_title][subsection_title][rownum][resrv_colname]
                                    if table_reservation_line == "":
                                        dictionarized_topics_tables[topic][section_title][subsection_title][rownum][resrv_colname] = topic_reservation['reservation']
                                        #save table flag
                                        rewrite_table = True
                                    else:
                                        #check for conflict
                                        #if conflict:
                                        #print("Reservation conflict on page: {}")
                                        #notify
                                        table_reserving_user = get_user_names_from_line(table_reservation_line, unsigned_template_name, user_namespace)[0]
                                        if table_reserving_user != user:
                                            subpage_link = f"{json_data['pages']['main_page']}/{json_data['pages']['topics']['main_topic_page']}/{subpage_title}"
                                            notification = f"{notifications['RESERVATION_CONFLICT']}".format(qcode=qcode, page=subpage_link, subpage_title=subpage_title)
                                            notification_list.append(notification)
                                    print(f"page {page.title()} was modified by user {user}!")
                                else:
                                    #else cancel reservation, and remove reservation from table if already there
                                    answers[qcode] = "expired"
                                    
                                    topic = qcode_dict[qcode][0]["topic"]
                                    section_title = qcode_dict[qcode][0]["section_title"]
                                    subsection_title = qcode_dict[qcode][0]["subsection_title"]
                                    rownum = qcode_dict[qcode][0]["rownum"]
                                    table_reservation_line = dictionarized_topics_tables[topic][section_title][subsection_title][rownum][resrv_colname]
                                    if table_reservation_line != "":
                                        #check for conflict
                                        table_reserving_users = get_user_names_from_line(table_reservation_line, unsigned_template_name, user_namespace)
                                        #dictionarized_topics_tables[topic][section_title][subsection_title][rownum][resrv_colname] = topic_reservation['reservation']
                                        if table_reserving_users is not None:
                                            if table_reserving_users[0] != user:
                                                subpage_link = f"{json_data['pages']['main_page']}/{json_data['pages']['topics']['main_topic_page']}/{subpage_title}"
                                                notification = f"{notifications['RESERVATION_CONFLICT']}".format(qcode=qcode, page=subpage_link, subpage_title=subpage_title)
                                                notification_list.append(notification)
                                        else:
                                            dictionarized_topics_tables[topic][section_title][subsection_title][rownum][resrv_colname] = ""
                                            rewrite_table = True
                                    print(f"page {page.title()} has not been modified by user {user}!")
                                
                        
                        
                        #make sure to check for conflicting reservations
                        #print(topic_reservation['reservation'])
                        #print(topic_reservation['reserved_topics'])
                        
                    else:
                        #copy reservation to table row(s)
                        pass

                topic_page_title = f"{json_data['pages']['main_page']}/{json_data['pages']['topics']['main_topic_page']}/{subpage_title}"
                topic_page = pywikibot.Page(site,topic_page_title)
                tmp_text = topic_page.text
                if len(answers)>0:
                    
                    #answer = json_data['reservation_answers']['cancel_reservation_not_modified']
                    message = process_answers(answers,json_data)
                    INLINE_RESERVATION_PROCESSING = json_data['SAVE_MESSAGES_DICT']['INLINE_RESERVATION_PROCESSING']
                    print(user)
                    print(message)
                    print(topic_reservation['reservation'],f"{topic_reservation['reservation']}\n{message}")
                    print(reserved_topics)
                    print(topic_reservation['date'])
                    tmp_text = tmp_text.replace(topic_reservation['reservation'],f"{topic_reservation['reservation']}\n{message}")

                if rewrite_table:
                    updated_table = hf.list_of_dicts_to_wikitext_table(dictionarized_topics_tables[topic][section_title][subsection_title])
                    tmp_text = tmp_text.replace(topics_tables[topic][section_title][subsection_title],updated_table)
                if tmp_text != topic_page.text:
                    print("updating topics page")
                    INTABLE_RESERVATION_PROCESSING = json_data['SAVE_MESSAGES_DICT']['INTABLE_RESERVATION_PROCESSING']
                    topic_page.text = tmp_text
                    topic_page.save(INTABLE_RESERVATION_PROCESSING)
                
            
        """
        if user in jury:
            notification_list.append(f"{notifications['NO_JURY_PARTICIPANTS']}")
        if user in organizers:
            notification_list.append(f"{notifications['NO_ORGANIZER_PARTICIPANTS']}")
        
        for qcode in reservations:
            if qcode not in topic_qcodes:
                notification_list.append(f"{notifications['TOPIC_NOT_ON_LIST']}")
        """
    print("pretreated_raw_reservations")
    for user, reservations in pretreated_raw_reservations["user_reservations"].items():
        if is_not_valid_participant(user,participants,jury,organizers,bot):
            #print(user)
            #print(bot)
            subpage_title = list(reservations.keys())[0]
            #print(subpage_title)
            subpage_link = f"{json_data['pages']['main_page']}/{json_data['pages']['topics']['main_topic_page']}/{subpage_title}"
            formatted_user_str = "{{"+f"{json_data['translations']['templates']['user_template']}|{user}{json_data['translations']['templates']['optional_user_template_param']}"+"}}"
            new_notification = f"{notifications['USER_NOT_REGISTERED']}".format(user=formatted_user_str, subpage_link=subpage_link, subpage_title=subpage_title)
            if new_notification[:-8] not in notifications_page.text:
                notification_list.append(new_notification)


    #validate reservations in tables
    #model content: {"topic":topic,"section_title":section_title,"subsection_title":subsection_title,"rownum":i
                #,"reservation_line":table[i][resrv_colname],'date':date,'':'reserved_code':extract_qcodes(table[i]['topic'])}
    print("raw_table_reservations")
    for user, reservations in raw_table_reservations["user_reservations"].items():
        
        
        if is_not_valid_participant(user,participants,jury,organizers,bot):
            #print(user)
            subpage_title = reservations[0]["topic"]
            subpage_link = f"{json_data['pages']['main_page']}/{json_data['pages']['topics']['main_topic_page']}/{subpage_title}"
            formatted_user_str = "{{"+f"{json_data['translations']['templates']['user_template']}|{user}{json_data['translations']['templates']['optional_user_template_param']}"+"}}"
            new_notification = f"{notifications['USER_NOT_REGISTERED']}".format(user=formatted_user_str, subpage_link=subpage_link, subpage_title=subpage_title)
            if new_notification[:-4] not in notifications_page.text:
                notification_list.append(new_notification)

        else:
            for reservation in reservations:
                answers = {}
                subpage_title = reservation["topic"]
                #print(subpage_title)
                #if subpage_title == "تاريخ": #to observe changes on a particular page
                if True:
                    topic_page_title = f"{json_data['pages']['main_page']}/{json_data['pages']['topics']['main_topic_page']}/{subpage_title}"
                    topic_page = pywikibot.Page(site,topic_page_title)
                    tmp_text = topic_page.text
                    if hf.is_more_than_one_day_old(reservation['date']):
                        #check if each reserved topic has been modified by the user in the alloted time
                        qcode = reservation['reserved_code']
                        #print(qcode)
                        page = hf.get_wikipedia_page(qcode, lang)
                        
                        if page is None:
                            
                            #print(f"page for language {lang} with qcode {qcode} doesn't exist!")
                            #cancel reservation
                            answers[qcode] = "expired"

                            message = process_answers(answers,json_data)
                            print(message)
                            
                            table_resevration_line = get_inline_reservation_line_from_table_reservation(reservation['reservation_line'],qcode,json_data)
                            if table_resevration_line not in tmp_text:
                                tmp_text+=f"\n*{table_resevration_line}\n{message}"
                            #print(f"Potentially suspicious line: {reservation['reservation_line']}")
                            #print(f"*{reservation['reservation_line']}\n{message}")
                                        
                        #remove reservation from table if already there
                        elif hf.user_modified_page_since(page, user, reservation['date']):
                            #check if there's no conflicting reservation in another table by another participant
                            #can only happen if the topic is invoked in multiple tables
                            #no such case for arwiki
                            if len(qcode_dict[qcode]) > 1:
                                print("WARNING!!!!! ",qcode, qcode_dict[qcode])
                            
                            #approve reservation in-line
                            answers[qcode] = "accepted"
                            #print(f"page {page.title()} was modified by user {user}!")
                            message = process_answers(answers,json_data)
                            #print(message)
                            
                            table_resevration_line = get_inline_reservation_line_from_table_reservation(reservation['reservation_line'],qcode,json_data)
                            if table_resevration_line not in tmp_text:
                                tmp_text+=f"\n*{table_resevration_line}\n{message}"
                            #print(f"Potentially suspicious line: {reservation['reservation_line']}")
                            #print(f"*{reservation['reservation_line']}\n{message}")
                            
                        else:
                            #print(reservation['date'])
                            #print(user)
                            #print(list(page.revisions(reverse=True, starttime=datetime(2023, 4, 25, 0, 0), endtime=min(datetime.now(), datetime(2023, 6, 10, 11, 59)))))
                            #else cancel reservation, and remove reservation from table if already there
                            answers[qcode] = "expired"
                            #print("rownum: ",qcode_dict[qcode][0]["rownum"])
                            #print(f"page {page.title()} has not been modified by user {user}!")

                            message = process_answers(answers,json_data)
                            #print(message)
                            #INTABLE_RESERVATION_PROCESSING = json_data['SAVE_MESSAGES_DICT']['INTABLE_RESERVATION_PROCESSING']
                            table_resevration_line = get_inline_reservation_line_from_table_reservation(reservation['reservation_line'],qcode,json_data)
                            if table_resevration_line not in tmp_text:
                                tmp_text+=f"\n*{table_resevration_line}\n{message}"
                            #print(f"Potentially suspicious line: {reservation['reservation_line']}")
                            #print(f"*{reservation['reservation_line']}\n{message}")

                          
                            
                            
                            
            if tmp_text != topic_page.text:
                #print("updating topics page")
                INTABLE_RESERVATION_PROCESSING = json_data['SAVE_MESSAGES_DICT']['INTABLE_RESERVATION_PROCESSING']
                topic_page.text = tmp_text
                topic_page.save(INTABLE_RESERVATION_PROCESSING)
                                        
                            
                            
            #make sure to check for conflicting reservations
            #print(topic_reservation['reservation'])
            #print(topic_reservation['reserved_topics'])
            '''       
            else:
                #copy reservation to table line and add response
                pass
            '''

    
    if len(notification_list)>0:
        notifications ='*'+'\n*'.join(notification_list)

        #print(notifications)

        #write_to_notification_page(notifications,notifications_page,json_data)
    
   
    output = topics_tables
    
    with open("output.txt","w",encoding="utf-8") as out:
        out.write(str(output))
    
    #write_notifications(site,notification_list,notification_page_title=f"{json_data['notification_page']}",save_message=f"{json_data['SAVE_MESSAGES_DICT']['save_to_notification_page']}")
    
    # Process the topic reservations
    
    # Handle reservations expiring after 24 hours
    #handle_expired_reservations()
    #'''
