import streamlit as st
import csv
from groq import Groq
import re

# Configuración de la página
st.set_page_config(page_title="Chatbot de Restaurante Moderado", page_icon="🍽️", layout="wide")

# Inicialización de variables de estado
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'menu' not in st.session_state:
    st.session_state.menu = {}
if 'delivery_cities' not in st.session_state:
    st.session_state.delivery_cities = set()
if 'initialized' not in st.session_state:
    st.session_state.initialized = False
if 'groq_available' not in st.session_state:
    st.session_state.groq_available = False

# Configuración de Groq
try:
    groq_api_key = st.secrets.get("GROQ_API_KEY")
    if groq_api_key:
        client = Groq(api_key=groq_api_key)
        st.session_state.groq_available = True
except Exception as e:
    print(f"Groq no está disponible: {e}")

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
            for row in reader:
                st.session_state.delivery_cities.add(f"{row['City']}, {row['State short']}")
        
        st.session_state.initialized = True
        return True
    except FileNotFoundError:
        st.error("Error: Archivos de datos no encontrados.")
        return False

def moderate_content(text):
    """Modera el contenido para filtrar lenguaje inapropiado."""
    # Lista de palabras inapropiadas (esto es solo un ejemplo, deberías expandirla)
    inappropriate_words = ['palabrota1', 'palabrota2', 'insulto1', 'insulto2']
    
    # Convertir el texto a minúsculas para la comparación
    text_lower = text.lower()
    
    # Verificar si alguna palabra inapropiada está en el texto
    if any(word in text_lower for word in inappropriate_words):
        return False, "Lo siento, tu mensaje contiene lenguaje inapropiado. Por favor, reformula tu pregunta de manera respetuosa."
    
    return True, text

def get_menu(category=None):
    """Devuelve el menú del restaurante de manera organizada."""
    if not st.session_state.menu:
        return "Lo siento, el menú no está disponible en este momento."
    
    if category and category in st.session_state.menu:
        menu_text = f"🍽️ Menú de {category}:\n\n"
        for item in st.session_state.menu[category]:
            menu_text += f"• {item['Item']} - {item['Serving Size']}\n"
    else:
        menu_text = "🍽️ Nuestro Menú:\n\n"
        for category, items in st.session_state.menu.items():
            menu_text += f"**{category}**\n"
            for item in items[:5]:  # Muestra solo los primeros 5 elementos de cada categoría
                menu_text += f"• {item['Item']} - {item['Serving Size']}\n"
            menu_text += "...\n\n"
        menu_text += "Para ver más detalles de una categoría específica, por favor pregúntame sobre ella."
    return menu_text

def get_delivery_info(city=None):
    """Verifica si se realiza entrega en una ciudad específica o muestra información general."""
    if not city:
        sample_cities = list(st.session_state.delivery_cities)[:10]
        return f"Realizamos entregas en muchas ciudades, incluyendo: {', '.join(sample_cities)}. Por favor, pregunta por una ciudad específica."
    
    city = city.title()  # Capitaliza la primera letra de cada palabra
    for delivery_city in st.session_state.delivery_cities:
        if city in delivery_city:
            return f"✅ Sí, realizamos entregas en {delivery_city}."
    return f"❌ Lo siento, no realizamos entregas en {city}. ¿Quieres que te muestre algunas ciudades cercanas donde sí entregamos?"

def get_bot_response(query):
    """Procesa la consulta del usuario y devuelve una respuesta."""
    # Primero, moderamos la consulta del usuario
    is_appropriate, moderated_query = moderate_content(query)
    if not is_appropriate:
        return moderated_query

    query_lower = moderated_query.lower()
    
    # Respuestas predefinidas para consultas comunes
    if any(word in query_lower for word in ["menú", "carta", "comida", "platos"]):
        return get_menu()
    elif any(word in query_lower for word in ["entrega", "reparto", "delivery"]):
        city = next((city for city in st.session_state.delivery_cities if city.split(',')[0].lower() in query_lower), None)
        return get_delivery_info(city.split(',')[0] if city else None)
    elif "horario" in query_lower:
        return "🕒 Nuestro horario es:\nLunes a Viernes: 11:00 AM - 10:00 PM\nSábados y Domingos: 10:00 AM - 11:00 PM"
    elif "especial" in query_lower:
        return "🌟 El especial de hoy es: Risotto de setas silvestres con trufa negra por $18.99"
    
    # Usar Groq para respuestas más complejas
    if st.session_state.groq_available:
        try:
            messages = [
                {"role": "system", "content": "Eres un asistente de restaurante amable y servicial. Tienes conocimiento sobre el menú, las entregas y los horarios del restaurante. Responde de manera concisa y directa. Evita cualquier contenido inapropiado o ofensivo."},
                {"role": "user", "content": moderated_query}
            ]
            response = client.chat.completions.create(
                messages=messages,
                model="mixtral-8x7b-32768",
                max_tokens=150,
                temperature=0.7
            )
            # Moderamos también la respuesta generada por Groq
            is_appropriate, moderated_response = moderate_content(response.choices[0].message.content)
            return moderated_response if is_appropriate else "Lo siento, no puedo proporcionar una respuesta apropiada a esa pregunta. ¿Puedo ayudarte con algo más relacionado con nuestro restaurante?"
        except Exception as e:
            print(f"Error al usar Groq: {e}")
    
    return "Lo siento, no pude entender tu consulta. ¿Puedo ayudarte con información sobre nuestro menú, entregas, horarios o especiales?"

def main():
    st.title("🍽️ Chatbot de Restaurante Moderado")
    
    if not st.session_state.initialized:
        load_data()
    
    st.write("Bienvenido a nuestro restaurante virtual. ¿En qué puedo ayudarte hoy?")
    
    # Mostrar mensajes anteriores
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Área de entrada del usuario
    if prompt := st.chat_input("Escribe tu mensaje aquí:"):
        # Moderar el mensaje del usuario antes de procesarlo
        is_appropriate, moderated_prompt = moderate_content(prompt)
        
        if is_appropriate:
            # Agregar mensaje del usuario al historial
            st.session_state.messages.append({"role": "user", "content": moderated_prompt})
            
            # Mostrar el mensaje del usuario
            with st.chat_message("user"):
                st.markdown(moderated_prompt)
            
            # Generar respuesta del chatbot
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                full_response = get_bot_response(moderated_prompt)
                message_placeholder.markdown(full_response)
            
            # Agregar respuesta del chatbot al historial
            st.session_state.messages.append({"role": "assistant", "content": full_response})
        else:
            # Mostrar mensaje de advertencia si el contenido es inapropiado
            st.warning(moderated_prompt)

if __name__ == "__main__":
    main()
