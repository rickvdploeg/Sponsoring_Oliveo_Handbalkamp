import streamlit as st
from google.oauth2.service_account import Credentials
import gspread
import pandas as pd
import time
import datetime
from PIL import Image


# Define URL's in the scope
scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive'
]

# Refer to the credentials in de secrets file
skey = st.secrets["gcp_service_account"]
credentials = Credentials.from_service_account_info(
    skey,
    scopes=scopes,
)
# Connect
client = gspread.authorize(credentials)

# Haal de boodschappenlijst op
boodschappenlijst_ruw = client.open('Sponsoring').worksheet('Boodschappenlijst')
boodschappenlijst = boodschappenlijst_ruw.get_all_values()
boodschappenlijst_df = pd.DataFrame(boodschappenlijst[1:], columns=boodschappenlijst[0])

# Haal de tot nu toe ingevulde sponsorlijst op
gesponsord_ruw = client.open('Sponsoring').worksheet("Gesponsord")
gesponsord = gesponsord_ruw.get_all_values()
gesponsord_df = pd.DataFrame(gesponsord[1:], columns=gesponsord[0])

# Haal wat al gesponsord is van de boodschappenlijst af
for item in gesponsord_df["Product"].unique():
    huidig_aantal = int(boodschappenlijst_df.loc[boodschappenlijst_df['Product'] == item, 'Aantal'].iloc[0])
    gesponsord_aantal = gesponsord_df.loc[gesponsord_df['Product'] == item, 'Aantal'].apply(int).sum()
    aantal_nog_over = huidig_aantal - gesponsord_aantal
    if aantal_nog_over <= 0:
         boodschappenlijst_df = boodschappenlijst_df[boodschappenlijst_df.Product != item]
    else:
         boodschappenlijst_df.loc[boodschappenlijst_df["Product"] == item, "Aantal"] = str(aantal_nog_over)

boodschappenlijst_dict = pd.Series(boodschappenlijst_df.Aantal.values, index=boodschappenlijst_df.Product).to_dict()
boodschappenlijst_dict["Anders, namelijk..."] = 99

# Define session_state to store the selected option and max value
if 'product' not in st.session_state:
    st.session_state.product = dict()
if 'aantal' not in st.session_state:
    st.session_state.aantal = dict()
if "num_filters" not in st.session_state:
    st.session_state["num_filters"] = 1
if "max_value_1" not in st.session_state:
    st.session_state["max_value_1"] = 1


def initialiseer_aantal():
    nr = st.session_state["num_filters"]
    if "max_value_{}".format(nr) not in st.session_state and "product_{}".format(nr) in st.session_state:
        st.session_state['max_value_{}'.format(nr)] = boodschappenlijst_dict[st.session_state['product_{}'.format(nr)]]


def update_aantal():
    nr = st.session_state.num_filters
    for i in range(1, nr + 1):
        if st.session_state['product_{}'.format(i)] == ' ':
            continue
        st.session_state['max_value_{}'.format(i)] = boodschappenlijst_dict[st.session_state['product_{}'.format(i)]]


# Bouw de app

# Less padding top of page
st.markdown("""
        <style>
               .block-container {
                    padding-top: 1rem;
                    padding-bottom: 0rem;
                    padding-left: 0.2rem;
                    padding-right: 0.2rem;
                }
        </style>
        """, unsafe_allow_html=True)


st.title("Handbalkamp sponsoring")
if boodschappenlijst_df.empty:
     st.info("Alle gewenste producten worden al gesponsord. Bedankt voor alle bijdrages en u kunt nog wel geld doneren m.b.v. de QR-code.")
else:
    placeholder = st.empty()
    with placeholder.expander("__Sponsor een product__"):
        st.write("Vul hier in wat u zou willen sponsoren. Er is een lijst aan boodschappen en aantalen die gewenst zijn. \
                Mocht een product er niet meer tussen staan, of weinig aantallen, dan worden deze al gesponsord.")
        #with st.form("formulier"):
        naam_sponsor = st.text_input("*Voor- en achternaam")
        email_sponsor = st.text_input("*Emailadres")

        for num in range(1, st.session_state["num_filters"] + 1):
            col1,col2 = st.columns([0.7, 0.3])
            index = len(st.session_state.product) if num > len(st.session_state.product) else num - 1

            with col1:
                st.session_state.product[num] = st.selectbox('Kies een product uit de lijst:', [" "] + list(boodschappenlijst_dict.keys()), key='product_{}'.format(num), index=index, on_change=update_aantal)

            initialiseer_aantal()

            with col2:
                st.session_state.aantal[num] = st.number_input("Kies het aantal:", min_value=1, max_value=int(st.session_state['max_value_{}'.format(num)]), key='aantal_{}'.format(num), disabled = True if st.session_state.product[num] == " " else False)

            # Create text input for user entry
            if st.session_state.product[num] == "Anders, namelijk...":
                st.session_state.product[num] = st.text_input("Beschrijf hier het product...", key='other_product_{}'.format(num), max_chars=100)

        col1,col2 = st.columns([0.7, 0.3])

        with col1:
            print(list(st.session_state.product.values()))
            if "" not in list(st.session_state.product.values()):
                if st.button("Sponsor nog een product", type='primary'):
                    st.session_state["num_filters"] += 1
                    st.experimental_rerun()

        opmerking = st.text_input("Eventuele opmerkingen:", max_chars=300)

        # Define the submit button
        if st.button("Verstuur", type='primary'):
            st.session_state.product = {key:val for key, val in st.session_state.product.items() if val not in ["", " "]}
            # Check if all required fields are filled in
            if naam_sponsor == '':
                st.error('Er moet een naam ingevuld zijn.')
            elif len(naam_sponsor) < 5 or " " not in naam_sponsor:
                st.error("Er moet een geldige voor- en achternaam ingevuld worden.")
            elif email_sponsor == '':
                st.error('Er moet een emailadres ingevuld zijn.')
            elif '@' not in email_sponsor or '.' not in email_sponsor:
                st.error("Er moet een geldig emailadres ingevuld worden.")
            elif len(st.session_state.product) == 0:
                st.error("Er moet minstens 1 product opgegeven zijn in het formulier.")
            elif len(st.session_state.product.values()) != len(set(st.session_state.product.values())):
                st.error("Een product komt meerdere keren voor in de lijst. Zorg dat ieder product maar 1x in de lijst voorkomt.")
            else:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for item in range(1, len(st.session_state.product)+1):
                    values = [naam_sponsor, email_sponsor, st.session_state.product[item], st.session_state.aantal[item], opmerking, timestamp]
                    gesponsord_ruw.append_row(values)
                st.session_state["num_filters"] = 1
                placeholder.success("Opgeslagen. Bedankt voor uw sponsoring!")
            #st.balloons()


with st.expander("__Sponsor geld__"):
    st.markdown("Scan de QR-code en volg de stappen, of volg deze [link](https://bunq.me/OHK).")
    col1,col2,col3 = st.columns([0.1, 0.8, 0.1])
    with col2:
        image = Image.open('QR code sponsoring kamp.PNG')
        st.image(image)

col1,col2,col3 = st.columns(3)
with col2:
   image = Image.open('./Logo Oliveo Handbal.PNG')
   st.image(image)