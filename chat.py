import streamlit as st
import os
import csv
from datetime import datetime
import random

# Intentar importar la librería OpenAI
try:
    import openai
    openai_available = True
except ImportError:
    st.error("Error: La librería 'openai' no está instalada. Algunas funcionalidades no estarán disponibles.")
    openai_available = False

# Inicialización del cliente OpenAI solo si está disponible
if openai_available:
    openai.api_key = st.secrets.get("OPENAI_API_KEY", "")

# Inicialización de variables de estado de Streamlit
if 'menu' not in st.session_state:
    st.session_state.menu = {}
if 'delivery_cities' not in st.session_state:
    st.session_state.delivery_cities = []
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'current_order' not in st.session_state:
    st.session_state.current_order = []
if 'order_in_progress' not in st.session_state:
    st.session_state.order_in_progress = False

def load_menu_from_csv():
    """
    Carga el menú desde un archivo CSV y lo almacena en el estado de la sesión.
    """
    try:
        with open('menu.csv', 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                category = row['Category']
                if category not in st.session_state.menu:
                    st.session_state.menu[category] = []
                st.session_state.menu[category].append(row)
    except FileNotFoundError:
        st.error("Error: El archivo 'menu.csv' no fue encontrado.")
    except KeyError as e:
        st.error(f"Error: La clave {e} no existe en el archivo 'menu.csv'. Verifica que los encabezados coincidan.")

def load_delivery_cities():
    """
    Carga las ciudades de entrega desde un archivo CSV y las almacena en el estado de la sesión.
    """
    try:
        with open('us-cities.csv', 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            st.session_state.delivery_cities = [f"{row['City']}, {row['State short']}" for row in reader]
    except FileNotFoundError:
        st.error("Error: El archivo 'us-cities.csv' no fue encontrado.")

def initialize_chatbot():
    """
    Inicializa el chatbot cargando el menú y las ciudades de entrega.
    """
    load_menu_from_csv()
    load_delivery_cities()
    st.success("¡Chatbot inicializado exitosamente!")

def moderate_content(message):
    """
    Modera el contenido del mensaje del usuario buscando palabras ofensivas.
    """
    offensive_words = ['palabrota1', 'palabrota2', 'palabrota3']  # Agrega más si es necesario
    return not any(word in message.lower() for word in offensive_words)

def process_user_query(query):
    """
    Procesa la consulta del usuario y dirige la lógica según las palabras clave.
    """
    if "menú" in query.lower() or "carta" in query.lower():
        return consult_menu_csv(query)
    elif "pedir" in query.lower() or "ordenar" in query.lower():
        return start_order_process(query)
    elif "cancelar" in query.lower() or "anular" in query.lower():
        return cancel_order()
    elif "confirmar" in query.lower():
        return confirm_order()
    elif "entrega" in query.lower() or "reparto" in query.lower():
        return consult_delivery_cities(query)
    else:
        return process_general_query(query)

def consult_menu_csv(query):
    """
    Consulta y devuelve el menú completo.
    """
    response = ""
    for category, items in st.session_state.menu.items():
        response += f"### {category}\n"
        for item in items:
            response += f"- **{item['Item']}**: {item['Serving Size']}, Precio: ${item['Price']}\n"
        response += "\n"
    return response

def start_order_process(query):
    """
    Inicia el proceso de pedido agregando un ítem al pedido actual.
    """
    st.session_state.order_in_progress = True
    # Suponiendo que el usuario dice algo como "Quiero pedir de [nombre del ítem]"
    item_name = query.split("de")[-1].strip().lower()
    for category, items in st.session_state.menu.items():
        for item in items:
            if item['Item'].lower() == item_name:
                st.session_state.current_order.append(item)
                return f"Has agregado **{item['Item']}** a tu pedido por un precio de ${item['Price']}. ¿Deseas algo más?"
    return "No encontré ese producto en nuestro menú. Por favor, intenta nuevamente."

def cancel_order():
    """
    Cancela el pedido en curso.
    """
    if st.session_state.order_in_progress:
        st.session_state.current_order = []
        st.session_state.order_in_progress = False
        return "Tu pedido ha sido cancelado."
    else:
        return "No tienes un pedido en curso para cancelar."

def confirm_order():
    """
    Confirma el pedido actual, calcula el precio total y lo guarda en el archivo CSV.
    """
    if st.session_state.order_in_progress and st.session_state.current_order:
        total_price = sum(float(item['Price']) for item in st.session_state.current_order)
        save_order_to_csv(st.session_state.current_order)
        st.session_state.order_in_progress = False
        st.session_state.current_order = []
        return f"Tu pedido ha sido confirmado. El precio total es ${total_price:.2f}. ¡Gracias por tu compra!"
    else:
        return "No tienes un pedido en curso para confirmar."

def save_order_to_csv(order):
    """
    Guarda el pedido confirmado en un archivo CSV.
    """
    filename = 'orders.csv'
    file_exists = os.path.isfile(filename)
    with open(filename, 'a', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Date', 'Item', 'Price']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        for item in order:
            writer.writerow({
                'Date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'Item': item['Item'],
                'Price': item['Price']
            })

def consult_delivery_cities(query):
    """
    Consulta y devuelve las ciudades donde se realiza la entrega.
    """
    response = "Realizamos entregas en las siguientes ciudades:\n"
    # Mostrar solo las primeras 10 ciudades para evitar una lista demasiado larga
    for city in st.session_state.delivery_cities[:10]:
        response += f"- {city}\n"
    response += "... y más ciudades. ¿Hay alguna ciudad específica que te interese?"
    return response

def process_general_query(query):
    """
    Procesa consultas generales utilizando la API de OpenAI si está disponible.
    """
    if openai_available:
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Eres un asistente de restaurante amable y servicial."},
                    {"role": "user", "content": query}
                ],
                max_tokens=500
            )
            return response.choices[0].message['content']
        except Exception as e:
            st.error(f"Error al procesar la consulta: {e}")
            return "Lo siento, ocurrió un error al procesar tu consulta."
    else:
        return "Lo siento, no puedo procesar consultas generales en este momento debido a limitaciones técnicas."

def generate_response(query_result):
    """
    Genera la respuesta que se mostrará al usuario.
    """
    return query_result

def main():
    # Configuración de la página
    st.set_page_config(page_title="Chatbot de Restaurante", page_icon="🍽️", layout="wide")

    # Encabezado
    st.title("Chatbot de Restaurante")

    st.markdown("---")

    # Botón para inicializar el chatbot
    if st.sidebar.button("Inicializar Chatbot"):
        initialize_chatbot()

    # Entrada de texto para el usuario
    user_message = st.text_input("Escribe tu mensaje aquí:", key="user_input")

    # Botón para enviar el mensaje
    if st.button("Enviar"):
        if not moderate_content(user_message):
            st.error("Lo siento, tu mensaje no es apropiado. Por favor, intenta de nuevo.")
        else:
            query_result = process_user_query(user_message)
            response = generate_response(query_result)

            # Guardar el historial de chat
            st.session_state.chat_history.append(("Usuario", user_message))
            st.session_state.chat_history.append(("Chatbot", response))

    # Mostrar historial de chat
    st.markdown("### Historial de Chat")
    chat_container = st.container()
    with chat_container:
        for role, message in st.session_state.chat_history:
            if role == "Usuario":
                st.markdown(
                    f"<div style='text-align: right; background-color: #00bfa5; color: white; padding: 10px; border-radius: 10px; margin: 5px 10px 5px 50px;'>{message}</div>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"<div style='text-align: left; background-color: #262626; color: #ffffff; padding: 10px; border-radius: 10px; margin: 5px 50px 5px 10px;'>{message}</div>",
                    unsafe_allow_html=True
                )

    # Mostrar el pedido actual y el precio total
    if st.session_state.current_order:
        st.markdown("### Pedido Actual")
        order_items = [f"{item['Item']} - ${item['Price']}" for item in st.session_state.current_order]
        st.write(", ".join(order_items))
        total_price = sum(float(item['Price']) for item in st.session_state.current_order)
        st.write(f"**Precio Total:** ${total_price:.2f}")

    # Información del restaurante en el pie de página
    st.markdown("---")
    st.markdown("**Restaurante Sabores Deliciosos** | Teléfono: (123) 456-7890 | Dirección: Calle Falsa 123, Ciudad Gourmet")

if __name__ == "__main__":
    main()
