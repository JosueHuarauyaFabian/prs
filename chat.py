import streamlit as st
import csv

# Configuración de la página
st.set_page_config(page_title="Chatbot de Restaurante", page_icon="🍽️", layout="wide")

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

# Intentar configurar Groq
try:
    from groq import Groq
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

def get_menu():
    """Devuelve el menú del restaurante de manera organizada."""
    if not st.session_state.menu:
        return "Lo siento, el menú no está disponible en este momento."
    
    menu_text = "🍽️ Nuestro Menú:\n\n"
    for category, items in st.session_state.menu.items():
        menu_text += f"**{category}**\n"
        for item in items[:5]:  # Muestra solo los primeros 5 elementos de cada categoría
            menu_text += f"• {item['Item']} - {item['Serving Size']}\n"
        menu_text += "...\n\n"
    menu_text += "Para ver más detalles de una categoría específica, por favor pregúntame sobre ella."
    return menu_text

def get_category_menu(category):
    """Devuelve los elementos de una categoría específica del menú."""
    if category in st.session_state.menu:
        menu_text = f"🍽️ Menú de {category}:\n\n"
        for item in st.session_state.menu[category]:
            menu_text += f"• {item['Item']} - {item['Serving Size']}\n"
        return menu_text
    else:
        return f"Lo siento, no encontré la categoría '{category}' en nuestro menú."

def get_delivery_info(city):
    """Verifica si se realiza entrega en una ciudad específica."""
    city = city.title()  # Capitaliza la primera letra de cada palabra
    for delivery_city in st.session_state.delivery_cities:
        if city in delivery_city:
            return f"✅ Sí, realizamos entregas en {delivery_city}."
    return f"❌ Lo siento, no realizamos entregas en {city}. ¿Quieres que te muestre algunas ciudades cercanas donde sí entregamos?"

def get_bot_response(query):
    """Procesa la consulta del usuario y devuelve una respuesta."""
    query_lower = query.lower()
    
    if "menú" in query_lower or "carta" in query_lower:
        return get_menu()
    elif any(category.lower() in query_lower for category in st.session_state.menu.keys()):
        for category in st.session_state.menu.keys():
            if category.lower() in query_lower:
                return get_category_menu(category)
    elif "entrega" in query_lower or "reparto" in query_lower:
        for city in st.session_state.delivery_cities:
            if city.split(',')[0].lower() in query_lower:
                return get_delivery_info(city.split(',')[0])
        return "Por favor, especifica la ciudad para la que quieres consultar la entrega."
    elif "horario" in query_lower:
        return "🕒 Nuestro horario es:\nLunes a Viernes: 11:00 AM - 10:00 PM\nSábados y Domingos: 10:00 AM - 11:00 PM"
    elif "especial" in query_lower:
        return "🌟 El especial de hoy es: Risotto de setas silvestres con trufa negra por $18.99"
    else:
        if st.session_state.groq_available:
            try:
                response = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": "Eres un asistente de restaurante amable y servicial. Responde de manera concisa y directa."},
                        {"role": "user", "content": query}
                    ],
                    model="mixtral-8x7b-32768",
                    max_tokens=150,
                    temperature=0.7
                )
                return response.choices[0].message.content
            except Exception as e:
                print(f"Error al usar Groq: {e}")
        
        return "Lo siento, no pude entender tu consulta. ¿Puedo ayudarte con información sobre nuestro menú, entregas, horarios o especiales?"

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
            message_placeholder.markdown(full_response)
        
        # Agregar respuesta del chatbot al historial
        st.session_state.messages.append({"role": "assistant", "content": full_response})

if __name__ == "__main__":
    main()
