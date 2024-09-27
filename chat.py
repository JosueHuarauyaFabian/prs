import streamlit as st
import csv
from datetime import datetime
import random

# Inicialización de variables de estado de Streamlit
if 'menu' not in st.session_state:
    st.session_state.menu = {}
if 'delivery_cities' not in st.session_state:
    st.session_state.delivery_cities = []
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'groq_available' not in st.session_state:
    st.session_state.groq_available = False

# Inicialización silenciosa del cliente Groq
try:
    from groq import Groq
    if "GROQ_API_KEY" in st.secrets:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        st.session_state.groq_available = True
except:
    pass  # Silenciosamente maneja cualquier error o falta de configuración de Groq

def load_data():
    """Carga los datos del menú y las ciudades de entrega."""
    try:
        with open('menu.csv', 'r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                category = row['Category']
                if category not in st.session_state.menu:
                    st.session_state.menu[category] = []
                st.session_state.menu[category].append(row)
        
        with open('us-cities.csv', 'r') as file:
            reader = csv.DictReader(file)
            st.session_state.delivery_cities = [f"{row['City']}, {row['State short']}" for row in reader]
        
        return True
    except FileNotFoundError:
        return False

def load_delivery_cities():
    try:
        with open('us-cities.csv', 'r') as file:
            reader = csv.DictReader(file)
            st.session_state.delivery_cities = [f"{row['City']}, {row['State short']}" for row in reader]
        return True
    except FileNotFoundError:
        st.error("Error: us-cities.csv file not found.")
        return False

def initialize_chatbot():
    menu_loaded = load_menu_from_csv()
    cities_loaded = load_delivery_cities()
    if menu_loaded and cities_loaded:
        st.session_state.chatbot_initialized = True
        st.success("Chatbot initialized successfully!")
    else:
        st.warning("Chatbot initialized with limited functionality.")

def moderate_content(message):
    offensive_words = ['palabrota1', 'palabrota2', 'palabrota3']  # Add more as needed
    return not any(word in message.lower() for word in offensive_words)

def process_user_query(query):
    if not st.session_state.chatbot_initialized:
        return "Por favor, inicializa el chatbot primero usando el botón 'Inicializar Chatbot'."
    
    query_lower = query.lower()
    if "menú" in query_lower or "carta" in query_lower:
        return consult_menu_csv(query_lower)
    elif "pedir" in query_lower or "ordenar" in query_lower:
        return start_order_process(query_lower)
    elif "entrega" in query_lower or "reparto" in query_lower:
        return consult_delivery_cities(query_lower)
    elif "información nutricional" in query_lower or "calorías" in query_lower:
        return get_nutritional_info(query_lower)
    elif "desayuno" in query_lower or "breakfast" in query_lower:
        return get_breakfast_info()
    elif "horario" in query_lower:
        return get_restaurant_hours()
    elif "especial" in query_lower:
        return get_daily_specials()
    else:
        return process_general_query(query_lower)

def consult_menu_csv(query):
    if not st.session_state.menu:
        return "Lo siento, el menú no está disponible en este momento."
    response = "Aquí está nuestro menú:\n\n"
    for category, items in st.session_state.menu.items():
        response += f"{category}:\n"
        for item in items:
            response += f"- {item['Item']}: {item['Serving Size']}, {item['Calories']} calorías\n"
        response += "\n"
    return response

def get_nutritional_info(query):
    if not st.session_state.menu:
        return "Lo siento, la información nutricional no está disponible en este momento."
    item_name = query.split("de ")[-1].strip().lower()
    for category, items in st.session_state.menu.items():
        for item in items:
            if item['Item'].lower() == item_name:
                return f"Información nutricional para {item['Item']}:\n" \
                       f"Tamaño de porción: {item['Serving Size']}\n" \
                       f"Calorías: {item['Calories']}\n" \
                       f"Grasa total: {item['Total Fat']}g ({item['Total Fat (% Daily Value)']}% del valor diario)\n" \
                       f"Sodio: {item['Sodium']}mg ({item['Sodium (% Daily Value)']}% del valor diario)\n" \
                       f"Carbohidratos: {item['Carbohydrates']}g ({item['Carbohydrates (% Daily Value)']}% del valor diario)\n" \
                       f"Proteínas: {item['Protein']}g"
    return "Lo siento, no pude encontrar información nutricional para ese artículo."

def start_order_process(query):
    if not st.session_state.menu:
        return "Lo siento, no puedo procesar pedidos en este momento."
    category = random.choice(list(st.session_state.menu.keys()))
    order = random.choice(st.session_state.menu[category])
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"Orden registrada: {order['Item']} - Timestamp: {timestamp}"

def consult_delivery_cities(query):
    if not st.session_state.delivery_cities:
        return "Lo siento, la información de entrega no está disponible en este momento."
    response = "Realizamos entregas en las siguientes ciudades:\n"
    for city in st.session_state.delivery_cities[:10]:  # Mostrar solo las primeras 10 ciudades
        response += f"- {city}\n"
    response += "... y más ciudades. ¿Hay alguna ciudad específica que te interese?"
    return response

def get_breakfast_info():
    breakfast_items = [item for items in st.session_state.menu.values() for item in items if 'breakfast' in item['Item'].lower()]
    if breakfast_items:
        response = "Nuestras opciones de desayuno incluyen:\n"
        for item in breakfast_items:
            response += f"- {item['Item']}: {item['Serving Size']}, {item['Calories']} calorías\n"
        return response
    else:
        return "Lo siento, no tenemos información específica sobre desayunos en este momento."

def get_restaurant_hours():
    return "Nuestro horario de atención es:\nLunes a Viernes: 7:00 AM - 10:00 PM\nSábados y Domingos: 8:00 AM - 11:00 PM"

def get_daily_specials():
    return "El especial del día de hoy es: Pasta Primavera con ensalada César por $12.99"

def get_general_response(query):
    """Procesa consultas generales usando Groq si está disponible."""
    if st.session_state.groq_available:
        try:
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "Eres un asistente de restaurante amable y servicial."},
                    {"role": "user", "content": query}
                ],
                model="mixtral-8x7b-32768",
                max_tokens=500
            )
            return chat_completion.choices[0].message.content
        except:
            pass  # Silenciosamente maneja cualquier error de Groq
    return "Lo siento, no puedo responder a esa pregunta en este momento. ¿Puedo ayudarte con el menú, horarios o especiales?"
def main():
    st.title("Chatbot de Restaurante")
    
    if 'initialized' not in st.session_state:
        if load_data():
            st.session_state.initialized = True
        else:
            st.error("No se pudo inicializar el chatbot. Algunas funciones pueden no estar disponibles.")
    
    st.write("¡Bienvenido a nuestro restaurante! ¿En qué puedo ayudarte hoy?")
    
    for message in st.session_state.chat_history:
        st.text(f"{'Tú:' if message[0] == 'Usuario' else 'Chatbot:'} {message[1]}")
    
    user_message = st.text_input("Escribe tu mensaje aquí:")
    
    if st.button("Enviar"):
        st.session_state.chat_history.append(("Usuario", user_message))
        bot_response = get_bot_response(user_message)
        st.session_state.chat_history.append(("Chatbot", bot_response))
        st.experimental_rerun()

if __name__ == "__main__":
    main()
