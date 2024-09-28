import streamlit as st
import csv
from groq import Groq
import json
from datetime import datetime
import os

# Configuración de la página
st.set_page_config(page_title="Chatbot de Restaurante", page_icon="🍽️", layout="wide")

# Inicialización de variables de estado
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'menu' not in st.session_state:
    st.session_state.menu = {}
if 'delivery_districts' not in st.session_state:
    st.session_state.delivery_districts = set()
if 'current_order' not in st.session_state:
    st.session_state.current_order = []
if 'formal_tone' not in st.session_state:
    st.session_state.formal_tone = True
if 'initialized' not in st.session_state:
    st.session_state.initialized = False

# Configuración de Groq
groq_api_key = st.secrets.get("GROQ_API_KEY")
client = Groq(api_key=groq_api_key)

def load_data():
    """Carga los datos del menú y los distritos de reparto."""
    try:
        with open('menu.csv', 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                category = row['Category']
                if category not in st.session_state.menu:
                    st.session_state.menu[category] = []
                st.session_state.menu[category].append(row)
        
        with open('delivery_districts.txt', 'r', encoding='utf-8') as file:
            st.session_state.delivery_districts = set(file.read().splitlines())
        
        st.session_state.initialized = True
        return True
    except FileNotFoundError:
        st.error("Error: Archivos de datos no encontrados.")
        return False

def get_menu(category=None):
    """Devuelve el menú del restaurante de manera organizada."""
    if not st.session_state.menu:
        return "Lo siento, el menú no está disponible en este momento."
    
    if category and category in st.session_state.menu:
        menu_text = f"🍽️ Menú de {category}:\n\n"
        for item in st.session_state.menu[category]:
            menu_text += f"• {item['Item']} - ${item['Price']}\n"
    else:
        menu_text = "🍽️ Nuestro Menú:\n\n"
        for category, items in st.session_state.menu.items():
            menu_text += f"**{category}**\n"
            for item in items[:5]:
                menu_text += f"• {item['Item']} - ${item['Price']}\n"
            menu_text += "...\n\n"
        menu_text += "Para ver más detalles de una categoría específica, por favor pregúntame sobre ella."
    return menu_text

def get_delivery_info(district=None):
    """Verifica si se realiza entrega en un distrito específico o muestra información general."""
    if not district:
        return f"Realizamos entregas en los siguientes distritos: {', '.join(st.session_state.delivery_districts)}. Por favor, pregunta por un distrito específico."
    
    if district.lower() in [d.lower() for d in st.session_state.delivery_districts]:
        return f"✅ Sí, realizamos entregas en {district}."
    return f"❌ Lo siento, no realizamos entregas en {district}. Los distritos disponibles son: {', '.join(st.session_state.delivery_districts)}."

def add_to_order(item, quantity):
    """Añade un ítem al pedido actual."""
    for category in st.session_state.menu.values():
        for menu_item in category:
            if menu_item['Item'].lower() == item.lower():
                st.session_state.current_order.append({
                    'item': menu_item['Item'],
                    'quantity': quantity,
                    'price': float(menu_item['Price'])
                })
                return f"Añadido al pedido: {quantity} x {menu_item['Item']}"
    return f"Lo siento, no pude encontrar '{item}' en nuestro menú."

def finalize_order():
    """Finaliza el pedido actual y lo registra."""
    if not st.session_state.current_order:
        return "No hay ítems en tu pedido actual."
    
    total = sum(item['quantity'] * item['price'] for item in st.session_state.current_order)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    order_details = {
        'timestamp': timestamp,
        'items': st.session_state.current_order,
        'total': total
    }
    
    # Registrar el pedido en un archivo JSON
    if not os.path.exists('orders.json'):
        with open('orders.json', 'w') as f:
            json.dump([], f)
    
    with open('orders.json', 'r+') as f:
        orders = json.load(f)
        orders.append(order_details)
        f.seek(0)
        json.dump(orders, f, indent=4)
    
    st.session_state.current_order = []
    return f"Pedido finalizado. Total: ${total:.2f}. Gracias por tu compra!"

def verify_response(response):
    """Verifica que la respuesta sea precisa antes de retornarla al usuario."""
    # Aquí podrías implementar verificaciones más complejas
    if len(response) < 10:
        return False, "La respuesta es demasiado corta. Por favor, elabora más."
    if len(response) > 500:
        return False, "La respuesta es demasiado larga. Por favor, sé más conciso."
    return True, response

def adjust_tone(response, formal=True):
    """Ajusta el tono de la respuesta según la preferencia del usuario."""
    if formal:
        # Reemplazar expresiones informales con formales
        response = response.replace("Hola", "Saludos")
        response = response.replace("Chao", "Hasta luego")
        # Añade más reemplazos según sea necesario
    else:
        # Reemplazar expresiones formales con informales
        response = response.replace("Saludos", "Hola")
        response = response.replace("Hasta luego", "Chao")
        # Añade más reemplazos según sea necesario
    return response

def get_bot_response(query):
    """Procesa la consulta del usuario y devuelve una respuesta."""
    query_lower = query.lower()
    
    if "menú" in query_lower or "carta" in query_lower:
        return get_menu()
    elif "entrega" in query_lower or "reparto" in query_lower:
        for district in st.session_state.delivery_districts:
            if district.lower() in query_lower:
                return get_delivery_info(district)
        return get_delivery_info()
    elif "pedir" in query_lower or "ordenar" in query_lower:
        # Procesamiento simple de pedidos
        items = re.findall(r'(\d+)\s*x\s*(.+?)(?=\d+\s*x|\s*y\s*|\s*,|$)', query_lower)
        if items:
            responses = []
            for quantity, item in items:
                responses.append(add_to_order(item.strip(), int(quantity)))
            return "\n".join(responses)
        else:
            return "No pude entender tu pedido. Por favor, especifica la cantidad y el nombre del plato, por ejemplo: '2 x pizza margherita'."
    elif "finalizar pedido" in query_lower:
        return finalize_order()
    elif "cambiar tono" in query_lower:
        st.session_state.formal_tone = not st.session_state.formal_tone
        return f"Tono cambiado a {'formal' if st.session_state.formal_tone else 'informal'}."
    
    # Usar Groq para respuestas más complejas
    try:
        messages = [
            {"role": "system", "content": "Eres un asistente de restaurante amable y servicial. Responde de manera concisa y precisa."},
            {"role": "user", "content": query}
        ]
        response = client.chat.completions.create(
            messages=messages,
            model="mixtral-8x7b-32768",
            max_tokens=150,
            temperature=0.7
        )
        is_valid, verified_response = verify_response(response.choices[0].message.content)
        if is_valid:
            return adjust_tone(verified_response, st.session_state.formal_tone)
        else:
            return verified_response
    except Exception as e:
        print(f"Error al usar Groq: {e}")
        return "Lo siento, no pude procesar tu consulta. ¿Puedo ayudarte con el menú, entregas o realizar un pedido?"

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
