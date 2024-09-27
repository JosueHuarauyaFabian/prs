import streamlit as st
import os
import csv
from datetime import datetime
import random
from groq import Groq
# Inicialización del cliente Groq
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    st.session_state.groq_available = True
except Exception as e:
    st.error(f"Error al inicializar el cliente Groq: {e}")
    st.session_state.groq_available = False


# Inicialización de variables de estado de Streamlit
if 'menu' not in st.session_state:
    st.session_state.menu = {}
if 'delivery_cities' not in st.session_state:
    st.session_state.delivery_cities = []
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

def load_menu_from_csv():
    try:
        with open('menu.csv', 'r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                category = row['Category']
                if category not in st.session_state.menu:
                    st.session_state.menu[category] = []
                st.session_state.menu[category].append(row)
    except FileNotFoundError:
        st.error("Error: menu.csv file not found.")

def load_delivery_cities():
    try:
        with open('us-cities.csv', 'r') as file:
            reader = csv.DictReader(file)
            st.session_state.delivery_cities = [f"{row['City']}, {row['State short']}" for row in reader]
    except FileNotFoundError:
        st.error("Error: us-cities.csv file not found.")

def initialize_chatbot():
    load_menu_from_csv()
    load_delivery_cities()
    st.success("Chatbot initialized successfully!")

def moderate_content(message):
    offensive_words = ['palabrota1', 'palabrota2', 'palabrota3']  # Add more as needed
    return not any(word in message.lower() for word in offensive_words)

def process_user_query(query):
    if "menú" in query.lower() or "carta" in query.lower():
        return consult_menu_csv(query)
    elif "pedir" in query.lower() or "ordenar" in query.lower():
        return start_order_process(query)
    elif "entrega" in query.lower() or "reparto" in query.lower():
        return consult_delivery_cities(query)
    elif "información nutricional" in query.lower() or "calorías" in query.lower():
        return get_nutritional_info(query)
    else:
        return process_general_query(query)

def consult_menu_csv(query):
    response = "Aquí está nuestro menú:\n\n"
    for category, items in st.session_state.menu.items():
        response += f"{category}:\n"
        for item in items:
            response += f"- {item['Item']}: {item['Serving Size']}, {item['Calories']} calorías\n"
        response += "\n"
    return response

def get_nutritional_info(query):
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
    category = random.choice(list(st.session_state.menu.keys()))
    order = random.choice(st.session_state.menu[category])
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"Orden registrada: {order['Item']} - Timestamp: {timestamp}"

def consult_delivery_cities(query):
    response = "Realizamos entregas en las siguientes ciudades:\n"
    for city in st.session_state.delivery_cities[:10]:  # Mostrar solo las primeras 10 ciudades
        response += f"- {city}\n"
    response += "... y más ciudades. ¿Hay alguna ciudad específica que te interese?"
    return response

def process_general_query(query):
    if st.session_state.groq_available:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Eres un asistente de restaurante amable y servicial."},
                {"role": "user", "content": query}
            ],
            model="mixtral-8x7b-32768",
            max_tokens=500
        )
        return chat_completion.choices[0].message.content
    else:
        return "Lo siento, no puedo procesar consultas generales en este momento debido a limitaciones técnicas."

def generate_response(query_result):
    if st.session_state.groq_available:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Eres un asistente de restaurante amable y servicial."},
                {"role": "user", "content": f"Basado en la siguiente información: '{query_result}', genera una respuesta amigable y natural para un cliente de restaurante:"}
            ],
            model="mixtral-8x7b-32768",
            max_tokens=150
        )
        return chat_completion.choices[0].message.content
    else:
        return query_result  # Fallback to original query result if Groq is not available

def main():
    st.title("Chatbot de Restaurante")
    
    
    
    if st.button("Inicializar Chatbot"):
        initialize_chatbot()
    
    user_message = st.text_input("Escribe tu mensaje aquí:")
    
    if st.button("Enviar"):
        if not moderate_content(user_message):
            st.error("Lo siento, tu mensaje no es apropiado. Por favor, intenta de nuevo.")
        else:
            query_result = process_user_query(user_message)
            response = generate_response(query_result)
            
            st.session_state.chat_history.append(("Usuario", user_message))
            st.session_state.chat_history.append(("Chatbot", response))
    
    st.subheader("Historial de Chat")
    for role, message in st.session_state.chat_history:
        st.text(f"{role}: {message}")

if __name__ == "__main__":
    main()
