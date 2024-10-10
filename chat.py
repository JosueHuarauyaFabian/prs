import streamlit as st
import pandas as pd
import re
from openai import OpenAI
import json
import logging
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# Configuración de logging
logging.basicConfig(level=logging.DEBUG)

# Configuración de la página
st.set_page_config(page_title="Chatbot de Restaurante", page_icon="🍽️")

# Inicialización del cliente OpenAI
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Configuración de Google Sheets
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
gc = gspread.authorize(creds)

# Abrir la hoja de cálculo
sheet = gc.open_by_url("https://docs.google.com/spreadsheets/d/1Tk-pUY47zj8KvYd6Qu4PpJNxC60IZOqBK_7-a0INoH0/edit?usp=sharing").sheet1

# Cargar datos
@st.cache_data
def load_data():
    try:
        menu_df = pd.read_csv('menu.csv')
        cities_df = pd.read_csv('us-cities.csv')
        return menu_df, cities_df['City'].tolist()
    except Exception as e:
        logging.error(f"Error al cargar los datos: {e}")
        return pd.DataFrame(), []

menu_df, delivery_cities = load_data()
if menu_df.empty:
    st.error("No se pudo cargar el menú. Por favor, verifica el archivo menu.csv.")
else:
    logging.info(f"Menú cargado correctamente. Categorías: {', '.join(menu_df['Category'].unique())}")

# Funciones de manejo del menú
def get_menu():
    if menu_df.empty:
        return "Lo siento, no pude cargar el menú. Por favor, contacta al soporte técnico."
    
    menu_text = "🍽️ Nuestro Menú:\n\n"
    for category, items in menu_df.groupby('Category'):
        menu_text += f"**{category}**\n"
        for _, item in items.iterrows():
            menu_text += f"• {item['Item']} - {item['Serving Size']} - ${item['Price']:.2f}\n"
        menu_text += "\n"
    menu_text += "Para ver más detalles de una categoría específica, por favor pregúntame sobre ella."
    return menu_text

def get_category_details(category):
    category_items = menu_df[menu_df['Category'] == category]
    if category_items.empty:
        return f"Lo siento, no encontré información sobre la categoría '{category}'."
    
    details = f"Detalles de {category}:\n\n"
    for _, item in category_items.iterrows():
        details += f"• {item['Item']} - {item['Serving Size']} - ${item['Price']:.2f}\n"
    return details

# Funciones de manejo de entregas
def check_delivery(city):
    if city.lower() in [c.lower() for c in delivery_cities]:
        return f"✅ Sí, realizamos entregas en {city}."
    else:
        return f"❌ Lo siento, actualmente no realizamos entregas en {city}."

def get_delivery_cities():
    return "Realizamos entregas en las siguientes ciudades:\n" + "\n".join(delivery_cities[:10]) + "\n..."

# Funciones de manejo de pedidos
def calculate_total():
    total = sum(menu_df.loc[menu_df['Item'] == item, 'Price'].iloc[0] * quantity 
                for item, quantity in st.session_state.current_order.items())
    return total

def add_to_order(item, quantity):
    if item in menu_df['Item'].values:
        if item in st.session_state.current_order:
            st.session_state.current_order[item] += quantity
        else:
            st.session_state.current_order[item] = quantity
        total = calculate_total()
        return f"Se ha añadido {quantity} {item}(s) a tu pedido. El total actual es ${total:.2f}"
    else:
        return f"Lo siento, {item} no está en nuestro menú. Por favor, verifica el menú e intenta de nuevo."

def remove_from_order(item):
    if item in st.session_state.current_order:
        del st.session_state.current_order[item]
        total = calculate_total()
        return f"Se ha eliminado {item} de tu pedido. El total actual es ${total:.2f}"
    return f"{item} no estaba en tu pedido."

def modify_order(item, quantity):
    if item in st.session_state.current_order:
        if quantity > 0:
            st.session_state.current_order[item] = quantity
        else:
            del st.session_state.current_order[item]
        total = calculate_total()
        return f"Se ha actualizado la cantidad de {item} a {quantity}. El total actual es ${total:.2f}"
    return f"{item} no está en tu pedido actual."

def start_order():
    st.session_state.order_stage = "collecting_items"
    return ("Para realizar un pedido, por favor sigue estos pasos:\n"
            "1. Dime qué items te gustaría ordenar\n"
            "2. Cuando hayas terminado, di 'Listo' o 'Finalizar pedido'\n"
            "3. Proporciona tu nombre y dirección de entrega\n"
            "4. Confirma tu pedido\n\n"
            "¿Qué te gustaría ordenar?")

def save_order_to_sheets(name, address, city, order, total):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    order_details = ", ".join([f"{item}: {quantity}" for item, quantity in order.items()])
    sheet.append_row([now, name, address, city, order_details, total])

def confirm_order(name, address, city):
    if not st.session_state.current_order:
        return "No hay ningún pedido para confirmar. ¿Quieres empezar uno nuevo?"
    
    total = calculate_total()
    save_order_to_sheets(name, address, city, st.session_state.current_order, total)
    
    order_summary = "Resumen del pedido:\n"
    for item, quantity in st.session_state.current_order.items():
        order_summary += f"• {quantity} x {item}\n"
    order_summary += f"\nTotal: ${total:.2f}"
    order_summary += f"\nNombre: {name}"
    order_summary += f"\nDirección: {address}"
    order_summary += f"\nCiudad: {city}"
    
    st.session_state.current_order = {}
    st.session_state.order_stage = "completed"
    return f"¡Gracias por tu pedido! Ha sido confirmado y guardado.\n\n{order_summary}"

def cancel_order():
    st.session_state.current_order = {}
    st.session_state.order_stage = "not_started"
    return "Tu pedido ha sido cancelado."

def show_current_order():
    if not st.session_state.current_order:
        return "No tienes ningún pedido en curso."
    order_summary = "Tu pedido actual:\n"
    total = 0
    for item, quantity in st.session_state.current_order.items():
        price = menu_df.loc[menu_df['Item'] == item, 'Price'].iloc[0]
        item_total = price * quantity
        total += item_total
        order_summary += f"• {quantity} x {item} - ${item_total:.2f}\n"
    order_summary += f"\nTotal: ${total:.2f}"
    return order_summary

# Función de filtrado de contenido
def is_inappropriate(text):
    inappropriate_words = ['palabrota1', 'palabrota2', 'insulto1', 'insulto2']
    return any(word in text.lower() for word in inappropriate_words)

# Función de manejo de consultas
def handle_query(query):
    if is_inappropriate(query):
        return "Por favor, mantén un lenguaje respetuoso."
    
    query_lower = query.lower()
    
    if "menu" in query_lower or "carta" in query_lower:
        return get_menu()
    elif re.search(r'\b(entrega|reparto)\b', query_lower):
        city_match = re.search(r'en\s+(\w+)', query_lower)
        if city_match:
            return check_delivery(city_match.group(1))
        else:
            return get_delivery_cities()
    elif re.search(r'\b(pedir|ordenar|pedido)\b', query_lower):
        return start_order()
    elif re.search(r'\b(categoría|categoria)\b', query_lower):
        category_match = re.search(r'(categoría|categoria)\s+(\w+)', query_lower)
        if category_match:
            return get_category_details(category_match.group(2))
    elif re.search(r'\b(precio|costo)\b', query_lower):
        item_match = re.search(r'(precio|costo)\s+de\s+(.+)', query_lower)
        if item_match:
            item = item_match.group(2)
            price = menu_df.loc[menu_df['Item'].str.lower() == item.lower(), 'Price']
            if not price.empty:
                return f"El precio de {item} es ${price.iloc[0]:.2f}"
            else:
                return f"Lo siento, no encontré el precio de {item}."
    elif "mostrar pedido" in query_lower:
        return show_current_order()
    elif "cancelar pedido" in query_lower:
        return cancel_order()
    elif "listo" in query_lower or "finalizar pedido" in query_lower:
        if st.session_state.order_stage == "collecting_items":
            st.session_state.order_stage = "collecting_info"
            return "Perfecto. Ahora, por favor proporciona tu nombre, dirección y ciudad de entrega."
    elif st.session_state.order_stage == "collecting_info":
        info_match = re.search(r'nombre:\s*(.+?),\s*dirección:\s*(.+?),\s*ciudad:\s*(.+)', query_lower)
        if info_match:
            name, address, city = info_match.groups()
            return confirm_order(name, address, city)
        else:
            return "No pude entender la información proporcionada. Por favor, proporciona tu nombre, dirección y ciudad en el formato: Nombre: [tu nombre], Dirección: [tu dirección], Ciudad: [tu ciudad]"
    
    # Manejo de pedidos
    if st.session_state.order_stage == "collecting_items":
        order_match = re.findall(r'(\d+)\s*(.*?)(?=\d+\s*|$)', query_lower)
        if order_match:
            response = ""
            for quantity, item in order_match:
                item = item.strip()
                response += add_to_order(item, int(quantity)) + "\n"
            return response.strip()
    
    # Si no se reconoce la consulta, usamos OpenAI para generar una respuesta
    try:
        messages = st.session_state.messages + [{"role": "user", "content": query}]
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": m["role"], "content": m["content"]}
                for m in messages
            ],
            max_tokens=150,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"Error generating response with OpenAI: {e}")
        return "Lo siento, no pude entender tu consulta. ¿Podrías reformularla?"

# Inicialización del estado de la sesión
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "¡Hola! Bienvenido a nuestro restaurante. ¿En qué puedo ayudarte hoy? Si quieres ver nuestro menú, solo pídemelo."}
    ]
if "current_order" not in st.session_state:
    st.session_state.current_order = {}
if "order_stage" not in st.session_state:
    st.session_state.order_stage = "not_started"

# Interfaz de usuario
st.title("🍽️ Chatbot de Restaurante")

# Mostrar mensajes existentes
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Campo de entrada para el usuario
if prompt := st.chat_input("¿En qué puedo ayudarte hoy?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = handle_query(prompt)
        message_placeholder.markdown(full_response)
    
    st.session_state.messages.append({"role": "assistant", "content": full_response})

# Mostrar el pedido actual
if st.session_state.current_order:
    st.sidebar.markdown("## Pedido Actual")
    st.sidebar.markdown(show_current_order())
    if st.sidebar.button("Cancelar Pedido"):
        st.sidebar.markdown(cancel_order())
