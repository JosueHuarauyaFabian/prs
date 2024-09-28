import streamlit as st
from groq import Groq
import csv

# Configuración de la página
st.set_page_config(page_title="Chatbot de Restaurante", page_icon="🍽️", layout="wide")

# Inicialización de variables de estado
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'menu' not in st.session_state:
    st.session_state.menu = {}
if 'delivery_cities' not in st.session_state:
    st.session_state.delivery_cities = []
if 'initialized' not in st.session_state:
    st.session_state.initialized = False

# Configuración de Groq
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception as e:
    st.error(f"Error al configurar Groq: {e}")
    st.stop()

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
        
        st.session_state.initialized = True
        return True
    except FileNotFoundError:
        st.error("Error: Archivos de datos no encontrados.")
        return False

def get_menu():
    """Devuelve el menú del restaurante."""
    if not st.session_state.menu:
        return "Lo siento, el menú no está disponible en este momento."
    
    menu_text = "🍽️ Aquí está nuestro menú:\n\n"
    for category, items in st.session_state.menu.items():
        menu_text += f"**{category}**\n"
        for item in items:
            menu_text += f"• {item['Item']} - {item['Serving Size']}\n"
        menu_text += "\n"
    return menu_text

def get_delivery_info(query):
    """Devuelve información sobre las ciudades de entrega."""
    if not st.session_state.delivery_cities:
        return "Lo siento, la información de entrega no está disponible en este momento."
    
    query_lower = query.lower()
    if "muestra" in query_lower or "lista" in query_lower:
        return f"🚚 Realizamos entregas en las siguientes ciudades:\n{', '.join(st.session_state.delivery_cities[:20])}\n... y más."
    
    for city in st.session_state.delivery_cities:
        if city.lower() in query_lower:
            return f"✅ Sí, realizamos entregas en {city}."
    
    return "❓ No he podido encontrar esa ciudad en nuestra lista de entregas. ¿Quieres que te muestre algunas ciudades disponibles?"

def get_bot_response(query):
    """Procesa la consulta del usuario y devuelve una respuesta."""
    query_lower = query.lower()
    
    if "menú" in query_lower or "carta" in query_lower:
        return get_menu()
    elif "entrega" in query_lower or "reparto" in query_lower:
        return get_delivery_info(query)
    elif "horario" in query_lower:
        return "🕒 Nuestro horario es:\nLunes a Viernes: 11:00 AM - 10:00 PM\nSábados y Domingos: 10:00 AM - 11:00 PM"
    elif "especial" in query_lower:
        return "🌟 El especial de hoy es: Risotto de setas silvestres con trufa negra por $18.99"
    else:
        return None  # Indica que se debe usar Groq para generar una respuesta

def main():
    st.title("🍽️ Chatbot de Restaurante")
    
    if not st.session_state.initialized:
        load_data()
    
    st.write("Bienvenido a nuestro restaurante virtual. ¿En qué puedo ayudarte hoy?")
    
    # Mostrar mensajes anteriores
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Área de entrada del usuario
    if prompt := st.chat_input("Escribe tu mensaje aquí:"):
        # Agregar mensaje del usuario al historial
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Mostrar el mensaje del usuario
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generar respuesta del chatbot
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = get_bot_response(prompt)
            
            if full_response is None:
                # Usar Groq para generar una respuesta
                full_response = ""
                for response in client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": "Eres un asistente de restaurante amable y servicial. Responde de manera concisa y directa."},
                        {"role": "user", "content": prompt}
                    ],
                    model="mixtral-8x7b-32768",
                    stream=True,
                ):
                    full_response += (response.choices[0].delta.content or "")
                    message_placeholder.markdown(full_response + "▌")
                message_placeholder.markdown(full_response)
            else:
                # Usar la respuesta predefinida
                message_placeholder.markdown(full_response)
        
        # Agregar respuesta del chatbot al historial
        st.session_state.messages.append({"role": "assistant", "content": full_response})

if __name__ == "__main__":
    main()
