import re

import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup


st.set_page_config(
    page_title="Origami Lead Finder",
    layout="wide"
)

st.title("Origami Lead Finder")
st.write(
    "Busca empresas con Google Places y analiza oportunidades de rediseño web."
)


API_KEY = st.secrets["GOOGLE_API_KEY"]


sector = st.text_input(
    "Sector",
    value="asesorías"
)

ciudad = st.text_input(
    "Ciudad",
    value="Vigo"
)

limite = st.number_input(
    "Número de resultados",
    min_value=1,
    max_value=100,
    value=20,
    step=1
)


def buscar_empresas_google(api_key, sector, ciudad, limite):
    url = "https://places.googleapis.com/v1/places:searchText"

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": (
            "places.id,"
            "places.displayName,"
            "places.formattedAddress,"
            "places.nationalPhoneNumber,"
            "places.websiteUri,"
            "places.googleMapsUri,"
            "nextPageToken"
        )
    }

    resultados = []
    page_token = None

    while len(resultados) < int(limite):
        cantidad_pagina = min(
            20,
            int(limite) - len(resultados)
        )

        body = {
            "textQuery": f"{sector} {ciudad}",
            "languageCode": "es",
            "pageSize": cantidad_pagina
        }

        if page_token:
            body["pageToken"] = page_token

        response = requests.post(
            url,
            headers=headers,
            json=body,
            timeout=30
        )

        if response.status_code != 200:
            st.error(
                f"Error de Google Places: {response.status_code}"
            )
            st.code(
                response.text,
                language="json"
            )
            break

        datos = response.json()

        for lugar in datos.get("places", []):
            resultados.append({
                "ID Google": lugar.get("id", ""),
                "Empresa": lugar.get(
                    "displayName",
                    {}
                ).get("text", ""),
                "Dirección": lugar.get(
                    "formattedAddress",
                    ""
                ),
                "Teléfono": lugar.get(
                    "nationalPhoneNumber",
                    ""
                ),
                "Web": lugar.get(
                    "websiteUri",
                    ""
                ),
                "Google Maps": lugar.get(
                    "googleMapsUri",
                    ""
                )
            })

            if len(resultados) >= int(limite):
                break

        page_token = datos.get("nextPageToken")

        if not page_token:
            break

    return resultados


def detectar_tecnologia(html, headers_respuesta):
    html_lower = html.lower()
    headers_texto = str(headers_respuesta).lower()

    if (
        "wp-content" in html_lower
        or "wp-includes" in html_lower
        or 'content="wordpress' in html_lower
    ):
        return "WordPress"

    if (
        "wixstatic.com" in html_lower
        or "wix.com" in html_lower
        or "wix-code" in html_lower
    ):
        return "Wix"

    if (
        "prestashop" in html_lower
        or "/modules/" in html_lower
    ):
        return "PrestaShop"

    if (
        "cdn.shopify.com" in html_lower
        or "shopify.theme" in html_lower
        or "myshopify.com" in html_lower
    ):
        return "Shopify"

    if (
        "/media/system/js/" in html_lower
        or 'content="joomla' in html_lower
        or "joomla!" in html_lower
    ):
        return "Joomla"

    if (
        "drupal-settings-json" in html_lower
        or "/sites/default/files/" in html_lower
        or 'content="drupal' in html_lower
    ):
        return "Drupal"

    if (
        "squarespace.com" in html_lower
        or "squarespace-cdn.com" in html_lower
    ):
        return "Squarespace"

    if (
        "webflow.io" in html_lower
        or "data-wf-page" in html_lower
    ):
        return "Webflow"

    if (
        "__next_data__" in html_lower
        or "/_next/static/" in html_lower
    ):
        return "Next.js"

    if (
        "ng-version=" in html_lower
        or "angular" in html_lower
    ):
        return "Angular"

    if (
        'id="root"' in html_lower
        and "react" in html_lower
    ):
        return "React"

    if (
        "laravel_session" in headers_texto
        or "laravel" in html_lower
    ):
        return "Laravel"

    if "bootstrap" in html_lower:
        return "HTML / Bootstrap"

    return "No identificada"


def analizar_web(url):
    datos = {
        "Email": "",
        "Tecnología": "No identificada",
        "SSL": "No",
        "Responsive": "Sí",
        "WhatsApp": "No",
        "Formulario": "No",
        "Google Analytics": "No",
        "Google Tag Manager": "No",
        "Meta Pixel": "No",
        "Cookies": "No detectado",
        "Facebook": "No",
        "Instagram": "No",
        "LinkedIn": "No",
        "Blog": "No",
        "Tienda online": "No",
        "Puntuación": 0,
        "Motivo para llamar": []
    }

    if not url:
        datos["Puntuación"] = 50
        datos["Motivo para llamar"].append(
            "No tiene página web indicada en Google"
        )
        datos["Motivo para llamar"] = "; ".join(
            datos["Motivo para llamar"]
        )
        return datos

    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "Chrome/124 Safari/537.36"
            )
        }

        response = requests.get(
            url,
            headers=headers,
            timeout=15,
            allow_redirects=True
        )

        response.raise_for_status()

        html_original = response.text
        html = html_original.lower()

        soup = BeautifulSoup(
            html_original,
            "html.parser"
        )

        datos["Tecnología"] = detectar_tecnologia(
            html_original,
            response.headers
        )

        texto = soup.get_text(
            " ",
            strip=True
        )

        emails = re.findall(
            r"[\w.\-+]+@[\w.\-]+\.\w+",
            texto
        )

        if emails:
            datos["Email"] = emails[0]

        if response.url.startswith("https://"):
            datos["SSL"] = "Sí"
        else:
            datos["SSL"] = "No"
            datos["Puntuación"] += 15
            datos["Motivo para llamar"].append(
                "No usa HTTPS"
            )

        viewport = soup.find(
            "meta",
            attrs={
                "name": re.compile(
                    "^viewport$",
                    re.I
                )
            }
        )

        if viewport is None:
            datos["Responsive"] = "No"
            datos["Puntuación"] += 20
            datos["Motivo para llamar"].append(
                "Puede no estar adaptada a móvil"
            )

        if (
            "whatsapp" in html
            or "wa.me" in html
            or "api.whatsapp.com" in html
        ):
            datos["WhatsApp"] = "Sí"
        else:
            datos["Puntuación"] += 8
            datos["Motivo para llamar"].append(
                "No tiene WhatsApp visible"
            )

        if soup.find("form"):
            datos["Formulario"] = "Sí"
        else:
            datos["Puntuación"] += 10
            datos["Motivo para llamar"].append(
                "No tiene formulario visible"
            )

        indicadores_analytics = [
            "googletagmanager.com/gtag/js",
            "google-analytics.com",
            "gtag(",
            "ga('create'",
            'ga("create"',
            "analytics.js",
            "measurement_id"
        ]

        if any(
            indicador in html
            for indicador in indicadores_analytics
        ):
            datos["Google Analytics"] = "Sí"
        else:
            datos["Puntuación"] += 5
            datos["Motivo para llamar"].append(
                "No se detecta Google Analytics"
            )

        indicadores_gtm = [
            "googletagmanager.com/gtm.js",
            "googletagmanager.com/ns.html",
            "gtm-"
        ]

        if any(
            indicador in html
            for indicador in indicadores_gtm
        ):
            datos["Google Tag Manager"] = "Sí"
        else:
            datos["Puntuación"] += 4

        indicadores_meta = [
            "connect.facebook.net",
            "fbq(",
            "facebook pixel",
            "meta pixel"
        ]

        if any(
            indicador in html
            for indicador in indicadores_meta
        ):
            datos["Meta Pixel"] = "Sí"

        indicadores_cookies = [
            "cookiebot",
            "cookieyes",
            "complianz",
            "iubenda",
            "onetrust",
            "cookie consent",
            "consentimiento de cookies",
            "política de cookies",
            "politica de cookies",
            "aceptar cookies",
            "configurar cookies"
        ]

        if any(
            indicador in html
            for indicador in indicadores_cookies
        ):
            datos["Cookies"] = "Sí"
        else:
            datos["Puntuación"] += 8
            datos["Motivo para llamar"].append(
                "No se detecta banner de cookies"
            )

        enlaces = [
            enlace.get("href", "").lower()
            for enlace in soup.find_all(
                "a",
                href=True
            )
        ]

        if any(
            "facebook.com" in enlace
            for enlace in enlaces
        ):
            datos["Facebook"] = "Sí"

        if any(
            "instagram.com" in enlace
            for enlace in enlaces
        ):
            datos["Instagram"] = "Sí"

        if any(
            "linkedin.com" in enlace
            for enlace in enlaces
        ):
            datos["LinkedIn"] = "Sí"

        indicadores_blog = [
            "/blog",
            "/noticias",
            "/actualidad",
            "/articulos",
            "/artículos"
        ]

        if any(
            indicador in html
            for indicador in indicadores_blog
        ):
            datos["Blog"] = "Sí"

        indicadores_tienda = [
            "woocommerce",
            "add-to-cart",
            "añadir al carrito",
            "agregar al carrito",
            "checkout",
            "/carrito",
            "/cart",
            "/shop",
            "prestashop",
            "shopify"
        ]

        if any(
            indicador in html
            for indicador in indicadores_tienda
        ):
            datos["Tienda online"] = "Sí"

        if len(html_original) < 5000:
            datos["Puntuación"] += 10
            datos["Motivo para llamar"].append(
                "Web muy básica o con poco contenido"
            )

        fechas_antiguas = re.findall(
            r"\b(?:200\d|201[0-8])\b",
            html
        )

        if fechas_antiguas:
            datos["Puntuación"] += 10
            datos["Motivo para llamar"].append(
                "Aparecen fechas antiguas en la web"
            )

    except requests.RequestException:
        datos["Puntuación"] += 30
        datos["Motivo para llamar"].append(
            "No se pudo analizar la web"
        )

    datos["Puntuación"] = min(
        datos["Puntuación"],
        100
    )

    datos["Motivo para llamar"] = "; ".join(
        datos["Motivo para llamar"]
    )

    return datos


if st.button("Buscar oportunidades"):
    if not API_KEY or API_KEY == "PON_AQUI_TU_API_KEY":
        st.error(
            "Debes poner tu clave de Google Places dentro del código."
        )
        st.stop()

    with st.spinner(
        "Buscando empresas en Google Places..."
    ):
        empresas = buscar_empresas_google(
            API_KEY,
            sector,
            ciudad,
            limite
        )

    if not empresas:
        st.warning(
            "No se encontraron empresas."
        )
        st.stop()

    filas = []

    progress = st.progress(0)
    total = len(empresas)

    for indice, empresa in enumerate(empresas):
        analisis = analizar_web(
            empresa["Web"]
        )

        filas.append({
            "Empresa": empresa["Empresa"],
            "Dirección": empresa["Dirección"],
            "Teléfono": empresa["Teléfono"],
            "Web": empresa["Web"],
            "Email": analisis["Email"],
            "Tecnología": analisis["Tecnología"],
            "SSL": analisis["SSL"],
            "Responsive": analisis["Responsive"],
            "WhatsApp": analisis["WhatsApp"],
            "Formulario": analisis["Formulario"],
            "Google Analytics": analisis["Google Analytics"],
            "Google Tag Manager": analisis["Google Tag Manager"],
            "Meta Pixel": analisis["Meta Pixel"],
            "Cookies": analisis["Cookies"],
            "Facebook": analisis["Facebook"],
            "Instagram": analisis["Instagram"],
            "LinkedIn": analisis["LinkedIn"],
            "Blog": analisis["Blog"],
            "Tienda online": analisis["Tienda online"],
            "Puntuación": analisis["Puntuación"],
            "Motivo para llamar": analisis["Motivo para llamar"],
            "Google Maps": empresa["Google Maps"]
        })

        progress.progress(
            (indice + 1) / total
        )

    df = pd.DataFrame(
        filas
    )

    df = df.sort_values(
        by="Puntuación",
        ascending=False
    )

    st.success(
        f"Se encontraron y analizaron {len(df)} empresas."
    )

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Web": st.column_config.LinkColumn(
                "Web",
                display_text="Abrir web"
            ),
            "Google Maps": st.column_config.LinkColumn(
                "Google Maps",
                display_text="Abrir Maps"
            )
        }
    )

    csv = df.to_csv(
        index=False
    ).encode("utf-8-sig")

    st.download_button(
        "Descargar resultados en CSV",
        data=csv,
        file_name="oportunidades_web.csv",
        mime="text/csv"
    )