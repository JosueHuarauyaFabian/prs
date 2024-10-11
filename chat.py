import streamlit as st
import pandas as pd
import re
from openai import OpenAI
import json
import logging
from enum import Enum

# Configuración de logging
logging.basicConfig(level=logging.DEBUG)

# Configuración de la página
st.set_page_config(page_title="Chatbot de Restaurante", page_icon="🍽️")

# Inicialización del cliente OpenAI
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Definir estados del pedido
class OrderState(Enum):
    INITIAL = 0
    SELECTING_ITEMS = 1
    CONFIRMING_ADDRESS = 2
    CONFIRMING_ORDER = 3

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

# Funciones de manejo del menú
def get_menu():
    menu_text = "🍽️ Nuestro Menú:\n\n"
    for category, items in menu_df.groupby('Category'):
        menu_text += f"**{category}**\n"
        for _, item in items.iterrows():
            menu_text += f"• {item['Item']} - {item['Serving Size']} - ${item['Price']:.2f}\n"
        menu_text += "\n"
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
    return sum(menu_df.loc[menu_df['Item'] == item, 'Price'].iloc[0] * quantity 
               for item, quantity in st.session_state.current_order.items())

def add_to_order(item, quantity):
    if item.lower() in [i.lower() for i in menu_df['Item']]:
        st.session_state.current_order[item] = st.session_state.current_order.get(item, 0) + quantity
        total = calculate_total()
        return f"Se ha añadido {quantity} {item}(s) a tu pedido. El total actual es ${total:.2f}"
    return f"Lo siento, {item} no está en nuestro menú. Por favor, verifica el menú e intenta de nuevo."

def confirm_order():
    if not st.session_state.current_order:
        return "No hay ningún pedido para confirmar. ¿Quieres empezar uno nuevo?"
    
    order_details = {
        'items': st.session_state.current_order,
        'total': calculate_total(),
        'address': st.session_state.delivery_address,
        'city': st.session_state.delivery_city
    }
    
    # Guardar el pedido localmente
    with open('orders.json', 'a') as f:
        json.dump(order_details, f)
        f.write('\n')
    
    st.session_state.current_order = {}
    st.session_state.order_state = OrderState.INITIAL
    return f"¡Gracias por tu pedido! Ha sido confirmado y guardado. El total es ${order_details['total']:.2f}"

# Función de manejo de consultas
def handle_query(query):
    query_lower = query.lower()
    
    if st.session_state.order_state == OrderState.INITIAL:
        if "menú" in query_lower or "carta" in query_lower:
            return get_menu()
        elif "pedir" in query_lower or "ordenar" in query_lower:
            st.session_state.order_state = OrderState.SELECTING_ITEMS
            return "¡Genial! ¿Qué te gustaría ordenar? Puedes decirme los platos y las cantidades."

    elif st.session_state.order_state == OrderState.SELECTING_ITEMS:
        items = extract_order_items(query)
        if items:
            response = ""
            for item, quantity in items:
                response += add_to_order(item, quantity) + "\n"
            return response + "¿Quieres algo más o estás listo para confirmar tu pedido?"
        elif "listo" in query_lower or "confirmar" in query_lower:
            st.session_state.order_state = OrderState.CONFIRMING_ADDRESS
            return "Perfecto. ¿Cuál es tu dirección de entrega y ciudad?"

    elif st.session_state.order_state == OrderState.CONFIRMING_ADDRESS:
        address, city = extract_address_and_city(query)
        if address and city:
            st.session_state.delivery_address = address
            st.session_state.delivery_city = city
            st.session_state.order_state = OrderState.CONFIRMING_ORDER
            return f"Gracias. Tu pedido será entregado en {address}, {city}. El total es ${calculate_total():.2f}. ¿Quieres confirmar tu pedido?"

    elif st.session_state.order_state == OrderState.CONFIRMING_ORDER:
        if "sí" in query_lower or "confirmar" in query_lower:
            return confirm_order()
        elif "no" in query_lower or "cancelar" in query_lower:
            st.session_state.order_state = OrderState.INITIAL
            st.session_state.current_order = {}
            return "Tu pedido ha sido cancelado. ¿Puedo ayudarte con algo más?"

    # Manejo de otras consultas
    if "entrega" in query_lower:
        city = extract_city(query)
        if city:
            return check_delivery(city)
        else:
            return get_delivery_cities()

    # Si no se reconoce la consulta, usar OpenAI
    return generate_ai_response(query)

# Funciones auxiliares
def extract_order_items(query):
    items = re.findall(r'(\d+)\s*([\w\s]+)', query)
    return [(item.strip(), int(quantity)) for quantity, item in items]

def extract_address_and_city(query):
    # Esta es una implementación simplificada. En un caso real, se necesitaría una lógica más robusta.
    parts = query.split(',')
    if len(parts) >= 2:
        return parts[0].strip(), parts[1].strip()
    return None, None

def extract_city(query):
    city_match = re.search(r'en\s+(\w+)', query)
    return city_match.group(1) if city_match else None

def generate_ai_response(query):
    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "Eres un asistente de restaurante amable y servicial."},
                {"role": "user", "content": query}
            ],
            max_tokens=150,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"Error generating response with OpenAI: {e}")
        return "Lo siento, no pude entender tu consulta. ¿Podrías reformularla?"

# Inicialización del estado de la sesión
if 'order_state' not in st.session_state:
    st.session_state.order_state = OrderState.INITIAL
if 'current_order' not in st.session_state:
    st.session_state.current_order = {}
if 'delivery_address' not in st.session_state:
    st.session_state.delivery_address = ""
if 'delivery_city' not in st.session_state:
    st.session_state.delivery_city = ""

# Interfaz de usuario de Streamlit
st.title("🍽️ Chatbot de Restaurante")

# Mostrar mensajes existentes
for message in st.session_state.get('messages', []):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Campo de entrada para el usuario
if prompt := st.chat_input("¿En qué puedo ayudarte hoy?"):
    st.session_state.messages = st.session_state.get('messages', []) + [{"role": "user", "content": prompt}]
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Generar respuesta del chatbot
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = handle_query(prompt)
        message_placeholder.markdown(full_response)
    
    st.session_state.messages.append({"role": "assistant", "content": full_response})

# Mostrar el estado actual del pedido en la barra lateral
st.sidebar.markdown("## Estado del Pedido")
st.sidebar.write(f"Estado: {st.session_state.order_state.name}")
if st.session_state.current_order:
    st.sidebar.markdown("### Pedido Actual:")
    for item, quantity in st.session_state.current_order.items():
        st.sidebar.write(f"{item}: {quantity}")
    st.sidebar.markdown(f"**Total: ${calculate_total():.2f}**")
