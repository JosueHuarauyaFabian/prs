import streamlit as st
import csv
import json
from datetime import datetime
import os
import re

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

# Lista básica de palabras inapropiadas
INAPPROPRIATE_WORDS = ['malasPalabras1', 'malasPalabras2', 'malasPalabras3']  # Añade las palabras que desees filtrar

def load_data():
    """Carga los datos del menú y las ciudades de entrega."""
    try:
        # Cargar el menú
        with open('menu.csv', 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file, delimiter='\t')  # Especificar el delimitador tabulación
            for row in reader:
                try:
                    category = row['Category']
                    item = row['Item']
                    serving_size = row['Serving Size']
                    price_str = row['Price'].strip()
                    price = float(price_str)
                    if category not in st.session_state.menu:
                        st.session_state.menu[category] = []
                    st.session_state.menu[category].append({
                        'Item': item,
                        'Serving Size': serving_size,
                        'Price': price
                    })
                except ValueError:
                    st.warning(f"Precio inválido para el ítem '{row.get('Item', 'Desconocido')}'. Se omitirá este ítem.")
                except KeyError as e:
                    st.error(f"Falta la columna {e} en el archivo menu.csv.")
                    return False

        # Cargar las ciudades de entrega
        with open('us-cities.csv', 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file, delimiter='\t')  # Especificar el delimitador tabulación
            for row in reader:
                city = row.get('City')
                state = row.get('State short')
                if city and state:
                    st.session_state.delivery_cities.append(f"{city}, {state}")

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
            menu_text += f"• **{item['Item']}** - {item['Serving Size']} - **${item['Price']:.2f}**\n"
    else:
        menu_text = "🍽️ **Nuestro Menú:**\n\n"
        for category, items in st.session_state.menu.items():
            menu_text += f"### {category}\n"
            for item in items:
                menu_text += f"• **{item['Item']}** - {item['Serving Size']} - **${item['Price']:.2f}**\n"
            menu_text += "\n"
        menu_text += "Para ver más detalles de una categoría específica, por favor pregúntame sobre ella."
    return menu_text

def get_delivery_info(city=None):
    """Verifica si se realiza entrega en una ciudad específica o muestra información general."""
    if not city:
        sample_cities = st.session_state.delivery_cities[:5]
        return f"Realizamos entregas en varias ciudades, incluyendo: {', '.join(sample_cities)}... y más. Por favor, pregunta por una ciudad específica."

    city = city.title()  # Capitaliza la primera letra de cada palabra
    for delivery_city in st.session_state.delivery_cities:
        if city in delivery_city:
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
                    'serving_size': menu_item['Serving Size'],
                    'price': menu_item['Price']
                })
                return f"Añadido al pedido: {quantity} x **{menu_item['Item']}** ({menu_item['Serving Size']}) - **${menu_item['Price']:.2f}** cada uno."
    return f"Lo siento, no pude encontrar '{item}' en nuestro menú."

def remove_from_order(item, quantity=None):
    """Remueve un ítem del pedido actual."""
    removed = False
    for order_item in st.session_state.current_order:
        if order_item['item'].lower() == item.lower():
            if quantity is None or order_item['quantity'] <= quantity:
                st.session_state.current_order.remove(order_item)
                removed = True
                return f"Removido del pedido: **{order_item['item']}**."
            else:
                order_item['quantity'] -= quantity
                removed = True
                return f"Removido del pedido: {quantity} x **{order_item['item']}**."
    if not removed:
        return f"No se encontró '{item}' en tu pedido."

def calculate_total():
    """Calcula el precio total del pedido actual."""
    total = sum(item['price'] * item['quantity'] for item in st.session_state.current_order)
    return total

def finalize_order():
    """Finaliza el pedido actual y lo registra."""
    if not st.session_state.current_order:
        return "No hay ítems en tu pedido actual."

    order_summary = "📝 **Resumen del pedido:**\n"
    for item in st.session_state.current_order:
        order_summary += f"• {item['quantity']} x **{item['item']}** ({item['serving_size']}) - **${item['price']:.2f}** cada uno\n"
    total = calculate_total()
    order_summary += f"\n**Total:** ${total:.2f}\n"

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    order_details = {
        'timestamp': timestamp,
        'items': st.session_state.current_order,
        'total': total
    }

    # Registrar el pedido en un archivo JSON
    if not os.path.exists('orders.json'):
        with open('orders.json', 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=4)

    with open('orders.json', 'r+', encoding='utf-8') as f:
        try:
            orders = json.load(f)
        except json.JSONDecodeError:
            orders = []
        orders.append(order_details)
        f.seek(0)
        json.dump(orders, f, ensure_ascii=False, indent=4)

    st.session_state.current_order = []
    return f"{order_summary}\n✅ **Pedido registrado con éxito a las {timestamp}. ¡Gracias por tu compra!**"

def cancel_order():
    """Cancela el pedido actual."""
    if not st.session_state.current_order:
        return "No hay ningún pedido para cancelar."
    st.session_state.current_order = []
    return "🛑 Tu pedido ha sido cancelado."

def get_bot_response(query):
    """Procesa la consulta del usuario y devuelve una respuesta."""
    # Filtrar comentarios inapropiados
    for word in INAPPROPRIATE_WORDS:
        if re.search(rf'\b{word}\b', query, re.IGNORECASE):
            return "⚠️ Lo siento, no puedo procesar comentarios inapropiados. Por favor, mantén la conversación respetuosa."

    query_lower = query.lower()

    if "menú" in query_lower or "carta" in query_lower:
        return get_menu()
    elif any(category.lower() in query_lower for category in st.session_state.menu.keys()):
        for category in st.session_state.menu.keys():
            if category.lower() in query_lower:
                return get_menu(category)
    elif "entrega" in query_lower or "reparto" in query_lower:
        for city in st.session_state.delivery_cities:
            if city.split(',')[0].lower() in query_lower:
                return get_delivery_info(city.split(',')[0])
        return get_delivery_info()
    elif "pedir" in query_lower or "ordenar" in query_lower:
        # Ejemplos de patrones: '2 x hamburguesa', '1x pizza', '3 x ensalada'
        items = re.findall(r'(\d+)\s*x\s*([\w\s&]+)', query_lower)
        if items:
            responses = []
            for quantity, item in items:
                responses.append(add_to_order(item.strip(), int(quantity)))
            total = calculate_total()
            responses.append(f"**Total actual:** ${total:.2f}")
            return "\n".join(responses)
        else:
            return "❓ No pude entender tu pedido. Por favor, especifica la cantidad y el nombre del plato, por ejemplo: '2 x hamburguesa'."
    elif "quitar" in query_lower or "remover" in query_lower:
        # Ejemplos de patrones: 'quitar hamburguesa', 'remover 1 x pizza'
        items = re.findall(r'(quitar|remover)\s+(\d+)?\s*x?\s*([\w\s&]+)', query_lower)
        if items:
            responses = []
            for action, quantity, item in items:
                if quantity:
                    responses.append(remove_from_order(item.strip(), int(quantity)))
                else:
                    responses.append(remove_from_order(item.strip()))
            total = calculate_total()
            responses.append(f"**Total actual:** ${total:.2f}")
            return "\n".join(responses)
        else:
            return "❓ No pude entender qué quieres remover. Por favor, usa el formato: 'quitar 2 x hamburguesa'."
    elif "finalizar pedido" in query_lower or "confirmar pedido" in query_lower:
        return finalize_order()
    elif "cancelar pedido" in query_lower:
        return cancel_order()
    elif "ver pedido" in query_lower or "mostrar pedido" in query_lower:
        if not st.session_state.current_order:
            return "🛒 Tu pedido está vacío."
        order_summary = "🛒 **Tu pedido actual:**\n"
        for item in st.session_state.current_order:
            order_summary += f"• {item['quantity']} x **{item['item']}** - **${item['price']:.2f}** cada uno\n"
        total = calculate_total()
        order_summary += f"\n**Total:** ${total:.2f}"
        return order_summary
    elif "horario" in query_lower:
        return "🕒 **Nuestro horario es:**\nLunes a Viernes: 11:00 AM - 10:00 PM\nSábados y Domingos: 10:00 AM - 11:00 PM"
    elif "especial" in query_lower:
        return "🌟 **El especial de hoy es:** Hamburguesa gourmet con papas fritas y bebida gratis."
    else:
        return "🤔 Lo siento, no entendí tu pregunta. ¿Puedo ayudarte con información sobre nuestro menú, entregas, realizar un pedido, cancelar un pedido o nuestro horario?"

def main():
    st.title("🍽️ Chatbot de Restaurante")

    if not st.session_state.initialized:
        load_data()

    st.write("👋 Bienvenido a nuestro restaurante virtual. ¿En qué puedo ayudarte hoy?")

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
