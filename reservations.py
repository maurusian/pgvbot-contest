import pywikibot, json, re, sys
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
def get_user_name_from_line(line, unsigned_template_name, user_namespace):
    user_names = re.findall(r'\[\[(?:' + re.escape(user_namespace) + r'|User):([^|\]]+)\|', line, flags=re.IGNORECASE)
    print(user_names)
    if not user_names:
        unsigned_match = re.search(r'{{' + re.escape(unsigned_template_name) + r'\|1=([^|}]+)', line)
        if unsigned_match:
            user_names.append(unsigned_match.group(1))

        if user_names:
            return user_names[0]
    else:
        return user_names[0]
    
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
    ignored_raw_reservations = {'user_reservations':{},'anonymous_reservations':{}}
    discarded_lines = []
    main_topic_page_title = f"{json_data['pages']['main_page']}/{json_data['pages']['topics']['main_topic_page']}"

    unsigned_template_name = json_data['translations']['templates']['unsigned_template']
    user_namespace = json_data['translations']['namespaces']['user']
    
    for subpage_title in json_data['pages']['topics']['subpages']:
        topic_page = pywikibot.Page(site,f"{main_topic_page_title}/{subpage_title}")
        #print(topic_page.title())
        print(subpage_title)
        #print(reservation_section_title)
        reservation_section = hf.get_section_by_title(topic_page.text, reservation_section_title)
        #print(reservation_section)
        if reservation_section is not None:
            reservation_lines = reservation_section.splitlines()
            for line in reservation_lines:
                if line.strip() != "" and line.strip() != "=== قائمة الحجز ===":
                    username = get_user_name_from_line(line, unsigned_template_name, user_namespace)
                    jury = json_data['jury']
                    organizers = json_data['organizers']
                    bot = json_data['bot']
                    if username is not None:
                        if username not in jury and username not in organizers:
                        
                            line_index = reservation_lines.index(line)
                            ignore_line = False
                            next_line = None
                            if line_index < len(reservation_lines)-1:
                                next_line = reservation_lines[line_index+1]
                                next_username = get_user_name_from_line(next_line, unsigned_template_name, user_namespace)
                                print(username)
                                print(next_username)
                                if next_username is not None and (next_username in jury or next_username in organizers or next_username == bot):
                                    
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
                                    if username not in ignored_raw_reservations['anonymous_reservations'].keys():
                                        ignored_raw_reservations['anonymous_reservations'][username] = {subpage_title:[{'reservation':line,'next_line':next_line,'reserved_topics':reserved_topics}]}
                                    else:
                                        if subpage_title not in ignored_raw_reservations['anonymous_reservations'][username].keys():
                                            ignored_raw_reservations['anonymous_reservations'][username][subpage_title] = [{'reservation':line,'next_line':next_line,'reserved_topics':reserved_topics}]
                                        else:
                                            ignored_raw_reservations['anonymous_reserations'][username][subpage_title].append({'reservation':line,'next_line':next_line,'reserved_topics':reserved_topics})
                                else:
                                    if username not in ignored_raw_reservations['user_reservations'].keys():
                                        ignored_raw_reservations['user_reservations'][username] = {subpage_title:[{'reservation':line,'next_line':next_line,'reserved_topics':reserved_topics}]}
                                    else:
                                        if subpage_title not in ignored_raw_reservations['user_reservations'][username].keys():
                                            ignored_raw_reservations['user_reservations'][username][subpage_title] = [{'reservation':line,'next_line':next_line,'reserved_topics':reserved_topics}]
                                        else:
                                            ignored_raw_reservations['user_reservations'][username][subpage_title].append({'reservation':line,'next_line':next_line,'reserved_topics':reserved_topics})
                            
                    elif username not in jury and username not in organizers:
                        #treat untreated unsigned reservations, treated unsigned reservations (followed by a response from an organizer or jury member are completely ignored)
                        line_index = reservation_lines.index(line)
                        ignore_line = False
                        next_line = None
                        if line_index < len(reservation_lines)-1:
                            next_line = reservation_lines[line_index+1]
                            next_username = get_user_name_from_line(next_line, unsigned_template_name, user_namespace)
                            print(username)
                            print(next_username)
                            if next_username is not None and (next_username in jury or next_username in organizers or next_username == bot):
                                    
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
                        
    return raw_reservations, ignored_raw_reservations, discarded_lines




def get_topic_qcodes(site,topics_tables):
    pass
        

def load_topics_tables(site,json_data):
    pass


def write_to_notification_page(notifications,notifications_page,json_data):
    SAVE_MESSAGE = f"{json_data['SAVE_MESSAGES_DICT']['NOTIFY']}"
    try:
        notifications_page.text+='\n'+notifications
        notifications_page.save(SAVE_MESSAGE)
    except:
        print("Could not save to notification page.")
        print(sys.exc_info())

# Main section
if __name__ == "__main__":
    lang = "ar"
    site = pywikibot.Site(lang,"wikipedia")
    json_page_title = f"Mediawiki:{lang}_translation.json"
    print(json_page_title)
    json_data = read_json_file(pywikibot.Site(JSON_SITE_LANG[lang],"wikipedia"), json_page_title)

    
    jury = json_data['jury']
    organizers = json_data['organizers']
    notifications = json_data['notifications']

    # Fetch the participant list and topic tables   
    participants = load_participants(site,json_data)
    topics_tables = load_topics_tables(site,json_data)
    raw_reservations, ignored_raw_reservations, discarded_lines = process_raw_reservations(site,json_data) #dictionary key = user, value = list of qcodes of reserved topics
    topic_qcodes = get_topic_qcodes(site,topics_tables)

    #print(raw_reservations["user_reservations"])

    #print(ignored_raw_reservations)

    #print(discarded_lines)

    #print(participants)

    #run checks and add to notification list
    
    notification_list = []
    notifications_page_title = f"{json_data['pages']['main_page']}/{json_data['pages']['notifications_page']}"
    print(notifications_page_title)
    notifications_page = pywikibot.Page(site,notifications_page_title)
    for user, reservations in raw_reservations["user_reservations"].items():
        if user not in participants:
            subpage_title = list(reservations.keys())[0]
            subpage_link = f"{json_data['pages']['main_page']}/{json_data['pages']['topics']['main_topic_page']}/{subpage_title}"
            formatted_user_str = "{{"+f"{json_data['translations']['templates']['user_template']}|{user}{json_data['translations']['templates']['optional_user_template_param']}"+"}}"
            new_notification = f"{notifications['USER_NOT_REGISTERED']}".format(user=formatted_user_str, subpage_link=subpage_link, subpage_title=subpage_title)
            if new_notification[:-4] not in notifications_page.text:
                notification_list.append(new_notification)
        """
        if user in jury:
            notification_list.append(f"{notifications['NO_JURY_PARTICIPANTS']}")
        if user in organizers:
            notification_list.append(f"{notifications['NO_ORGANIZER_PARTICIPANTS']}")
        
        for qcode in reservations:
            if qcode not in topic_qcodes:
                notification_list.append(f"{notifications['TOPIC_NOT_ON_LIST']}")
        """
    for user, reservations in ignored_raw_reservations["user_reservations"].items():
        if user not in participants:
            subpage_title = list(reservations.keys())[0]
            subpage_link = f"{json_data['pages']['main_page']}/{json_data['pages']['topics']['main_topic_page']}/{subpage_title}"
            formatted_user_str = "{{"+f"{json_data['translations']['templates']['user_template']}|{user}{json_data['translations']['templates']['optional_user_template_param']}"+"}}"
            new_notification = f"{notifications['USER_NOT_REGISTERED']}".format(user=formatted_user_str, subpage_link=subpage_link, subpage_title=subpage_title)
            if new_notification[:-4] not in notifications_page.text:
                notification_list.append(new_notification)

    
    
    notifications ='*'+'\n*'.join(notification_list)

    write_to_notification_page(notifications,notifications_page,json_data)
    
    #write_notifications(site,notification_list,notification_page_title=f"{json_data['notification_page']}",save_message=f"{json_data['SAVE_MESSAGES_DICT']['save_to_notification_page']}")
    
    # Process the topic reservations
    
    # Handle reservations expiring after 24 hours
    #handle_expired_reservations()
    
