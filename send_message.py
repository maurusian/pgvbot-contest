import pywikibot, json, os
from pywikibot.exceptions import NoPageError, IsRedirectPageError
import help_functions as hf
from pywikibot import pagegenerators
import pywikibot.flow


JSON_SITE_LANG = {"ar":"ary","ary":"ary","shi":"shi"}

def send_message_to_users(site, usernames, message_file, user_talk_namespace, save_message):
    #site = pywikibot.Site()
    site.login()

    try:
        with open(message_file, 'r', encoding="utf-8") as file:
            message = file.read()
            if message.strip() == "":
                print("file is empty!")
                return None
    except FileNotFoundError:
        print(f"The file {message_file} does not exist.")
        return
    except Exception as e:
        print(f"An error occurred while reading the file: {str(e)}")
        return

    for username in usernames:

        print(f'{user_talk_namespace}:{username}')
        user_talk_page = pywikibot.Page(site, f'{user_talk_namespace}:{username}')
        
        try:
            user_talk_page.get(get_redirect=True)  # Fetch the page content

        except IsRedirectPageError:
            print(f"User {username}'s talk page is a redirect.")
            continue
        except Exception as e:
            print(f"An error occurred while fetching the page: {str(e)}")
            continue
        """
        except NoPageError:
            print(f"User {username}'s talk page does not exist.")
            continue
        """
        title = 'تحديثات مسابقة ويكيبيديا المغرب 2023'
        signature = " ~~~~"
        content = message+signature
        if message not in user_talk_page.text:
            if user_talk_page.is_flow_page():
                board = pywikibot.flow.Board(user_talk_page)
                try:
                    topic = board.new_topic(title, content)
                except:
                    print(f'Error saving page: {sys.exc_info()}')
            else:
                if message[:-4] not in user_talk_page.text:
                    user_talk_page.text += f'\n\n== {title} ==\n{content}'
                    try:
                        user_talk_page.save(save_message)
                        print(f"Message sent to user {username}.")
                        
                    except Exception as e:
                        print(f"An error occurred while saving the page: {str(e)}")
                        continue

def get_users_with_min_edits(site, min_edits, excluded_users):
    #site = pywikibot.Site()
    metasite = pywikibot.Site('meta', 'meta')  # MetaWiki site
    site.login()

    users_with_min_edits = []

    for user in site.allusers(total=10000):  # total parameter adjusted according to your input
        username = user['name']
        with open("recent_log.txt","a", encoding="utf-8") as rl:
            rl.write(username+'\n')
        print(username)
        if username in excluded_users:
            continue

        
        user = pywikibot.User(site, username)
        if 'bot' in user.groups() or 'sysop' in user.groups():
            continue

        meta_user = pywikibot.User(metasite, username)
        if any(group in meta_user.groups() for group in ['steward', 'sysop', 'bureaucrat']):
            continue

        edit_count = 0
        contributions = pagegenerators.UserContributionsGenerator(username, site=site)

        for contrib in contributions:
            #print(contrib)
            #print(type(contrib))
            if not contrib.title().startswith('خدايمي:'):
                edit_count += 1

                if edit_count >= min_edits:
                    users_with_min_edits.append(username)
                    break

    return users_with_min_edits

USERS = """Daoudata
Xiquet
MassNssen
Lioneds
محب الخير للكل
W0
Zerothief
Mouradxmt
APAHEL
Aarp65
Abdeaitali
Achraf112
Ajwaan
Ali ahmed andalousi
Alitoar
Amherst99
Aymane34
Ayoub El Wardi
AyoubBouamriMa
AyourAchtouk
Cabayi
Céréales Killer
Daas sam
Dalinanir
DocPPicola
Douae Benaboud
El Tiko94
ElhoussaineDrissi
Elkhiar
Elmerrakchi
Enzoreg
Eru Rōraito
HitomiAkane
Iliass.Aymaz
J ansari
John.GGVV
Jon Harald Søby
Karimobo~incubatorwiki
MHMD DM
Marocsite
MdsShakil
Mehdi Immähder
Mohamed.mdb
MorGhost
Mr. Lechkar
Omar2040
Omarboulma1926
OussamaOuh
Revibot
Rida trissian
Romaine
Rotondus
SADIQUI
Saad Nabbi
Sadoki09
Sami At Ferḥat
SharryX
Siaahmed
Terbofast
Tifratin
Van hafidi
Yaakoub45
اشعاعاتى
سمير تامر
عصام أزناك"""

if __name__ == "__main__":
    #setup data
    lang = input("Enter lang code: ")
    if lang == "ar":
        site = pywikibot.Site(lang,"wikipedia")
        json_page_title = f"Mediawiki:{lang}_translation.json"
        json_data = hf.read_json_file(pywikibot.Site(JSON_SITE_LANG[lang],"wikipedia"), json_page_title)
        jury = json_data['jury']
        organizers = json_data['organizers']
        bot = json_data['bot']

        user_talk_namespace = json_data['translations']['namespaces']['user_talk_namespace']
        save_message = json_data['SAVE_MESSAGES_DICT']['DISSEMINATE_MESSAGE']
        
        usernames = hf.load_participants(site,json_data)
        
        message_file = 'message1.txt'  # The path to the message text file
        send_message_to_users(site,usernames, message_file, user_talk_namespace, save_message)

    
    elif lang == "ary":
        site = pywikibot.Site(lang,"wikipedia")
        json_page_title = f"Mediawiki:{lang}_translation.json"
        json_data = hf.read_json_file(pywikibot.Site(JSON_SITE_LANG[lang],"wikipedia"), json_page_title)
        jury = json_data['jury']
        print(jury)
        organizers = json_data['organizers']
        bot = json_data['bot']
        participants = hf.load_participants(site,json_data)

        treated_users = []
        if os.path.exists("recent_log.txt"):
            with open("recent_log.txt","r", encoding="utf-8") as rl:
                treated_users = rl.read().splitlines()

        excluded_users = jury
        excluded_users.extend(organizers)
        excluded_users.extend(participants)
        excluded_users.extend(treated_users)
        message_file = "message2.txt"
        min_edits = 10
        #usernames = get_users_with_min_edits(site, min_edits, excluded_users)
        save_message = "مصيفطة د ميصاج على ود مسابقة ويكيپيديا لمغريب"
        user_talk_namespace = "لمداكرة د لخدايمي"
        usernames = USERS.splitlines()
        send_message_to_users(site,usernames, message_file, user_talk_namespace, save_message)
        
