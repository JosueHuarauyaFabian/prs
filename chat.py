import streamlit as st
import csv
import json
from datetime import datetime
import os
import re
import difflib

# Configuración de la página
st.set_page_config(page_title="Chatbot de Restaurante", page_icon="🍽️", layout="wide")

# Inicialización de variables de estado
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'menu' not in st.session_state:
    st.session_state.menu = {}
if 'delivery_cities' not in st.session_state:
    st.session_state.delivery_cities = []
if 'current_order' not in st.session_state:
    st.session_state.current_order = []
if 'initialized' not in st.session_state:
    st.session_state.initialized = False
if 'current_page' not in st.session_state:
    st.session_state.current_page = 1

def load_data():
    """Carga los datos del menú y las ciudades de entrega."""
    try:
        # Cargar el menú
        with open('menu.csv', 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            headers = next(reader)  # Leer los encabezados
            for row in reader:
                if len(row) < 3:
                    continue  # Saltar filas incompletas
                category = row[0].strip()
                item = row[1].strip()
                serving_size = row[2].strip()
                if category not in st.session_state.menu:
                    st.session_state.menu[category] = []
                st.session_state.menu[category].append({
                    'Item': item,
                    'Serving Size': serving_size
                })

        # Cargar las ciudades de entrega (solo columna 'city')
        with open('us-cities.csv', 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            headers = next(reader)  # Leer los encabezados
            for row in reader:
                if len(row) >= 1:
                    city = row[0].strip()
                    st.session_state.delivery_cities.append(city)

        st.session_state.initialized = True
        return True
    except FileNotFoundError:
        st.error("Error: Archivos de datos no encontrados. Asegúrate de que 'menu.csv' y 'us-cities.csv' estén en el directorio correcto.")
        return False
    except Exception as e:
        st.error(f"Error al cargar los datos: {e}")
        return False

def get_menu(category=None):
    """Devuelve el menú del restaurante de manera organizada."""
    if not st.session_state.menu:
        return "Lo siento, el menú no está disponible en este momento."

    if category and category in st.session_state.menu:
        menu_text = f"🍽️ **Menú de {category}:**\n\n"
        for item in st.session_state.menu[category]:
            menu_text += f"• {item['Item']} - {item['Serving Size']}\n"
    else:
        menu_text = "🍽️ **Nuestro Menú:**\n\n"
        for category, items in st.session_state.menu.items():
            menu_text += f"**{category}**\n"
            for item in items[:5]:
                menu_text += f"• {item['Item']} - {item['Serving Size']}\n"
            if len(items) > 5:
                menu_text += "...\n"
            menu_text += "\n"
        menu_text += "Para ver más detalles de una categoría específica, por favor pregúntame sobre ella."
    return menu_text

def get_delivery_info(city=None):
    """Verifica si se realiza entrega en una ciudad específica o muestra información general."""
    if not city:
        sample_cities = st.session_state.delivery_cities[:5]
        return f"Realizamos entregas en varias ciudades, incluyendo: {', '.join(sample_cities)}... y más. Por favor, pregunta por una ciudad específica."

    # Capitaliza cada palabra para la comparación
    city = city.title()
    for delivery_city in st.session_state.delivery_cities:
        city_name = delivery_city.title()
        if city == city_name:
            return f"✅ Sí, realizamos entregas en {delivery_city}."
    return f"❌ Lo siento, no realizamos entregas en {city}. ¿Quieres que te muestre algunas ciudades donde sí entregamos?"

def add_to_order(item, quantity):
    """Añade un ítem al pedido actual."""
    for category in st.session_state.menu.values():
        for menu_item in category:
            if menu_item['Item'].lower() == item.lower():
                st.session_state.current_order.append({
                    'item': menu_item['Item'],
                    'quantity': quantity,
                    'serving_size': menu_item['Serving Size']
                })
                return f"Añadido al pedido: {quantity} x {menu_item['Item']} ({menu_item['Serving Size']})"
    return f"Lo siento, no pude encontrar '{item}' en nuestro menú."

def finalize_order():
    """Finaliza el pedido actual y lo registra."""
    if not st.session_state.current_order:
        return "No hay ítems en tu pedido actual."

    order_summary = "📝 **Resumen del pedido:**\n"
    for item in st.session_state.current_order:
        order_summary += f"• {item['quantity']} x {item['item']} ({item['serving_size']})\n"

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    order_details = {
        'timestamp': timestamp,
        'items': st.session_state.current_order
    }

    # Registrar el pedido en un archivo JSON
    if not os.path.exists('orders.json'):
        with open('orders.json', 'w') as f:
            json.dump([], f)

    with open('orders.json', 'r+') as f:
        try:
            orders = json.load(f)
        except json.JSONDecodeError:
            orders = []
        orders.append(order_details)
        f.seek(0)
        json.dump(orders, f, indent=4)

    st.session_state.current_order = []
    return f"{order_summary}\nPedido registrado con éxito a las {timestamp}. ¡Gracias por tu compra! 🍽️😊"

def get_all_delivery_cities():
    """Devuelve una lista completa de todas las ciudades de reparto."""
    if not st.session_state.delivery_cities:
        return "Actualmente, no tenemos ciudades de reparto disponibles."

    cities_per_page = 10  # Número de ciudades a mostrar por página
    total_cities = len(st.session_state.delivery_cities)
    total_pages = (total_cities + cities_per_page - 1) // cities_per_page

    def display_cities(page):
        start_idx = (page - 1) * cities_per_page
        end_idx = start_idx + cities_per_page
        return st.session_state.delivery_cities[start_idx:end_idx]

    response = "📍 **Lista Completa de Ciudades de Reparto:**\n\n"
    cities_to_display = display_cities(st.session_state.current_page)
    response += "\n".join(f"• {city}" for city in cities_to_display)

    # Navegación entre páginas
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.session_state.current_page > 1:
            if st.button("⬅️ Anterior"):
                st.session_state.current_page -= 1
                st.experimental_rerun()
    with col3:
        if st.session_state.current_page < total_pages:
            if st.button("Siguiente ➡️"):
                st.session_state.current_page += 1
                st.experimental_rerun()

    response += f"\n\nPágina {st.session_state.current_page} de {total_pages}."
    return response

def is_similar(word, target, threshold=0.8):
    """Verifica si dos palabras son similares por encima de un umbral."""
    return difflib.SequenceMatcher(None, word, target).ratio() > threshold

def get_bot_response(query):
    """Procesa la consulta del usuario y devuelve una respuesta."""
    query_lower = query.lower()

    if "menú" in query_lower or "carta" in query_lower:
        return get_menu()
    elif any(category.lower() in query_lower for category in st.session_state.menu.keys()):
        for category in st.session_state.menu.keys():
            if category.lower() in query_lower:
                return get_menu(category)
    elif "entrega" in query_lower or "reparto" in query_lower:
        # Detectar si el usuario pide todas las ciudades con tolerancia a errores tipográficos
        phrases = ["todas las ciudades", "lista completa", "todas las repartos", "mostrar todas", "ciudades de reparto", "cuidades de reparto"]
        if any(any(is_similar(word, phrase_word) for word in query_lower.split()) for phrase in phrases for phrase_word in phrase.split()):
            return get_all_delivery_cities()

        # Buscar si se menciona una ciudad específica
        words = re.findall(r'\b[A-Za-z]+(?:\s[A-Za-z]+)*\b', query)
        for word in words:
            city_candidate = word.strip().title()
            if city_candidate:
                # Comparar con las ciudades disponibles usando similitud
                for delivery_city in st.session_state.delivery_cities:
                    if is_similar(city_candidate, delivery_city, threshold=0.8):
                        return get_delivery_info(delivery_city)
        # Si no se encontró una ciudad específica
        return get_delivery_info()
    elif "pedir" in query_lower or "ordenar" in query_lower:
        items = re.findall(r'(\d+)\s*x\s*([a-zA-Z\s]+)', query_lower)
        if items:
            responses = []
            for quantity, item in items:
                response = add_to_order(item.strip(), int(quantity))
                responses.append(response)
            return "\n".join(responses)
        else:
            return "No pude entender tu pedido. Por favor, especifica la cantidad y el nombre del plato, por ejemplo: '2 x hamburguesa'."
    elif "finalizar pedido" in query_lower or "finalizar mi pedido" in query_lower:
        return finalize_order()
    elif "horario" in query_lower:
        return "🕒 **Nuestro horario es:**\n- **Lunes a Viernes:** 11:00 AM - 10:00 PM\n- **Sábados y Domingos:** 10:00 AM - 11:00 PM"
    elif "especial" in query_lower:
        return "🌟 **El especial de hoy es:** Hamburguesa gourmet con papas fritas"
    else:
        return "Lo siento, no entendí tu pregunta. ¿Puedo ayudarte con información sobre nuestro menú, entregas, realizar un pedido o nuestro horario?"

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
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = get_bot_response(prompt)
            message_placeholder.markdown(full_response)

        st.session_state.messages.append({"role": "assistant", "content": full_response})

if __name__ == "__main__":
    main()
