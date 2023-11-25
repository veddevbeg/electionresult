import telebot
import requests
from bs4 import BeautifulSoup
import pandas as pd
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

# Replace 'your_bot_token_here' with your actual bot token
BOT_TOKEN = '6101439029:AAHY8tK-HL4WGWGUCKpiZ05VEtDT6WUBFiQ'

# Create an instance of the TeleBot class
bot = telebot.TeleBot(BOT_TOKEN)

# Replace 'your_url_prefix' with the actual URL prefix
URL_PREFIX = 'https://results.eci.gov.in/ResultAcGenMay2023/ConstituencywiseS10'

# Load AC number and name mappings from Excel file
ac_mapping = {}

excel_file_path = 'ac_mapping.xlsx'  # Replace with your Excel file path

try:
    df = pd.read_excel(excel_file_path)
    df.columns = map(str.lower, df.columns)  # Convert column names to lowercase

    if 'ac_name' in df.columns and 'ac_number' in df.columns:
        ac_mapping = dict(zip(df['ac_name'].str.lower(), df['ac_number']))
    else:
        print("Error: Excel file does not have 'AC_Name' and 'AC_Number' columns.")
except Exception as e:
    print(f"Error reading Excel file: {e}")

print("AC Mapping:")
print(ac_mapping)

def is_valid_ac_number(text):
    try:
        # Try to convert the input to an integer to check if it's a valid AC number
        ac_number = int(text)
        return True
    except ValueError:
        return False

def get_ac_number(identifier):
    # If the identifier is a valid AC number, return it
    if is_valid_ac_number(identifier):
        return int(identifier)

    # If the identifier is a valid AC name, get the corresponding AC number
    return ac_mapping.get(identifier.lower(), None)

def is_valid_ac_identifier(identifier):
    # Check if the identifier is either a valid AC number or a valid AC name (including partial matches)
    return is_valid_ac_number(identifier) or any(fuzz.partial_ratio(identifier.lower(), ac.lower()) >= 80 for ac in ac_mapping)

@bot.message_handler(func=lambda message: is_valid_ac_identifier(message.text))
def get_result(message):
    try:
        identifier = message.text
        ac_number = get_ac_number(identifier)

        if ac_number is not None:
            url = f"{URL_PREFIX}{ac_number}.htm?ac={ac_number}"
            response = requests.get(url)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                div1 = soup.find('div', {'id': 'div1'})
                table = div1.find('table')
                rows = table.find_all('tr')

                ac_name = rows[0].find('td').text.strip()
                data_list = []

                for row in rows[3:-1]:
                    cells = row.find_all('td')
                    candidate = cells[1].text.strip()
                    party = cells[2].text.strip()
                    total_votes = int(cells[5].text.strip().replace(',', ''))
                    data_list.append({'Candidate': candidate, 'Party': party, 'Total Votes': total_votes})

                sorted_data = sorted(data_list, key=lambda x: x['Total Votes'], reverse=True)[:3]

                result_text = f"\n\n<b>Results for {ac_name} (AC {ac_number}):</b>\n\n"
                result_text += "\n\n".join([
                    f"<b>{i + 1}. Candidate:</b> {entry['Candidate']}\n<b>Party:</b> {entry['Party']}\n<b>Total Votes:</b> {entry['Total Votes']}"
                    for i, entry in enumerate(sorted_data)
                ])
                bot.send_message(message.chat.id, result_text, parse_mode='HTML')
            else:
                result_text = f"\n\nFailed to retrieve the webpage for AC {ac_number}. Status code: {response.status_code}"
                bot.send_message(message.chat.id, result_text, parse_mode='HTML')
        else:
            # Use fuzzy matching with fuzzywuzzy
            matches = process.extractOne(identifier.lower(), ac_mapping.keys())
            if matches[1] >= 80:  # Consider a match if the similarity score is above a threshold (adjust as needed)
                suggested_ac_number = ac_mapping[matches[0]]
                url = f"{URL_PREFIX}{suggested_ac_number}.htm?ac={suggested_ac_number}"
                response = requests.get(url)

                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    div1 = soup.find('div', {'id': 'div1'})
                    table = div1.find('table')
                    rows = table.find_all('tr')

                    ac_name = rows[0].find('td').text.strip()
                    data_list = []

                    for row in rows[3:-1]:
                        cells = row.find_all('td')
                        candidate = cells[1].text.strip()
                        party = cells[2].text.strip()
                        total_votes = int(cells[5].text.strip().replace(',', ''))
                        data_list.append({'Candidate': candidate, 'Party': party, 'Total Votes': total_votes})

                    sorted_data = sorted(data_list, key=lambda x: x['Total Votes'], reverse=True)[:3]

                    result_text = f"\n\n<b>Showing results for AC {suggested_ac_number}:</b>\n\n"
                    result_text += "\n\n".join([
                        f"<b>{i + 1}. Candidate:</b> {entry['Candidate']}\n<b>Party:</b> {entry['Party']}\n<b>Total Votes:</b> {entry['Total Votes']}"
                        for i, entry in enumerate(sorted_data)
                    ])
                    bot.send_message(message.chat.id, result_text, parse_mode='HTML')
                else:
                    result_text = f"\n\nFailed to retrieve the webpage for AC {suggested_ac_number}. Status code: {response.status_code}"
                    bot.send_message(message.chat.id, result_text, parse_mode='HTML')
            else:
                result_text = f"\n\nAC information not found for '{identifier}'."
                bot.send_message(message.chat.id, result_text, parse_mode='HTML')
    except ValueError:
        bot.reply_to(message, "Please provide a valid AC number or name.")

# Polling loop to keep the bot active
bot.polling()
