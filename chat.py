import streamlit as st
import os
import openai
import csv
from datetime import datetime
import random
from dotenv import load_dotenv, find_dotenv

# Cargar variables de entorno
load_dotenv(find_dotenv())

# Configurar la clave API de OpenAI
openai.api_key = os.getenv('OPENAI_API_KEY')

# Verificar si la clave API está configurada
if not openai.api_key:
    st.error("La clave API de OpenAI no está configurada. Por favor, configúrala en el archivo .env o en las variables de entorno.")
    st.stop()

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
    for category, items in menu.items():
        response += f"{category}:\n"
        for item in items:
            response += f"- {item['Item']}: {item['Serving Size']}, {item['Calories']} calorías\n"
        response += "\n"
    return response

def get_nutritional_info(query):
    item_name = query.split("de ")[-1].strip().lower()
    
    for category, items in menu.items():
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
    category = random.choice(list(menu.keys()))
    order = random.choice(menu[category])
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"Orden registrada: {order['Item']} - Timestamp: {timestamp}"

def consult_delivery_cities(query):
    response = "Realizamos entregas en las siguientes ciudades:\n"
    for city in delivery_cities[:10]:  # Mostrar solo las primeras 10 ciudades para no sobrecargar la respuesta
        response += f"- {city}\n"
    response += "... y más ciudades. ¿Hay alguna ciudad específica que te interese?"
    return response

def process_general_query(query):
    messages = [
        {'role': 'system', 'content': 'Eres un asistente de restaurante amable y servicial.'},
        {'role': 'user', 'content': query}
    ]
    return get_completion_from_messages(messages)

def get_completion_from_messages(messages, model="gpt-3.5-turbo", temperature=0, max_tokens=500):
    response = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message["content"]

def generate_response(query_result):
    prompt = f"Basado en la siguiente información: '{query_result}', genera una respuesta amigable y natural para un cliente de restaurante:"
    
    messages = [
        {"role": "system", "content": "Eres un asistente de restaurante amable y servicial."},
        {"role": "user", "content": prompt}
    ]
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=150,
            n=1,
            stop=None,
            temperature=0.7,
        )
        return response.choices[0].message["content"].strip()
    except Exception as e:
        print(f"Error al generar respuesta: {e}")
        return query_result  # Fallback to original query result if API call fails

def verify_response_accuracy(response, query_result):
    prompt = f"""
    Verifica si la siguiente respuesta es precisa y relevante según la información original:
    
    Información original: {query_result}
    Respuesta generada: {response}
    
    Responde con 'Preciso' si la respuesta es correcta y relevante, o 'Impreciso' si contiene errores o información irrelevante.
    """
    
    messages = [
        {"role": "system", "content": "Eres un asistente que verifica la precisión de las respuestas."},
        {"role": "user", "content": prompt}
    ]
    
    try:
        verification = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=10,
            n=1,
            stop=None,
            temperature=0.3,
        )
        result = verification.choices[0].message["content"].strip().lower()
        return "preciso" in result
    except Exception as e:
        print(f"Error al verificar respuesta: {e}")
        return True  # Assume accurate if verification fails

def regenerate_response(query_result):
    prompt = f"La respuesta anterior fue imprecisa. Genera una nueva respuesta basada en esta información: '{query_result}'. Asegúrate de que sea precisa y relevante."
    
    messages = [
        {"role": "system", "content": "Eres un asistente de restaurante que genera respuestas precisas y relevantes."},
        {"role": "user", "content": prompt}
    ]
    
    try:
        new_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=150,
            n=1,
            stop=None,
            temperature=0.5,
        )
        return new_response.choices[0].message["content"].strip()
    except Exception as e:
        print(f"Error al regenerar respuesta: {e}")
        return query_result  # Fallback to original query result if API call fails

def process_and_verify_response(query_result):
    response = generate_response(query_result)
    attempts = 0
    max_attempts = 3
    
    while attempts < max_attempts:
        if verify_response_accuracy(response, query_result):
            return response
        else:
            response = regenerate_response(query_result)
            attempts += 1
    
    return query_result  # Fallback to original query result if all attempts fail

def adjust_tone(response):
    messages = [
        {'role': 'system', 'content': 'Ajusta el tono del siguiente mensaje para que sea formal pero amigable.'},
        {'role': 'user', 'content': response}
    ]
    return get_completion_from_messages(messages)

def moderate_chatbot_response(response):
    offensive_words = ['palabrota1', 'palabrota2', 'palabrota3']  # Add more as needed
    return not any(word in response.lower() for word in offensive_words)
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
            response = process_and_verify_response(query_result)
            response = adjust_tone(response)
            
            if not moderate_chatbot_response(response):
                response = "Lo siento, no puedo proporcionar una respuesta adecuada en este momento."
            
            st.session_state.chat_history.append(("Usuario", user_message))
            st.session_state.chat_history.append(("Chatbot", response))
    
    st.subheader("Historial de Chat")
    for role, message in st.session_state.chat_history:
        st.text(f"{role}: {message}")

if __name__ == "__main__":
    main()
