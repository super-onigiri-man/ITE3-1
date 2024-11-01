import requests
import pandas as pd
import datetime
from datetime import timedelta, timezone
from cmcrameri import cm
import numpy as np
import pydeck as pdk
import streamlit as st  # Streamlitをインポート

# ストリームリット用ページ設定をスクリプトの最初に配置
st.set_page_config(page_title="10分間雨量", layout="wide", initial_sidebar_state="collapsed")

def get_data():
    now = datetime.datetime.now()
    adjusted_time = now - timedelta(minutes=10)
    adjusted_time = adjusted_time.replace(minute=(adjusted_time.minute // 10) * 10, second=0)
    jst = timezone(timedelta(hours=+9))
    adjusted_time_jst = adjusted_time.astimezone(jst)
    amedas_time = adjusted_time_jst.strftime('%Y%m%d%H%M%S')

    url = "https://www.jma.go.jp/bosai/amedas/data/map/" + str(amedas_time) + ".json"
    response = requests.get(url)
    data = response.json()
    df = pd.DataFrame.from_dict(data, orient='index')
    df = df[['temp', 'humidity', 'precipitation10m', 'precipitation1h', 'precipitation24h', 'windDirection', 'wind']]
    df.columns = ['気温', '湿度', '１０分間雨量', '１時間雨量', '２４時間雨量', '風向', '風速']
    for col in df.columns:
        df[col] = df[col].apply(lambda x: x[0] if isinstance(x, list) else x)

    url = "https://www.jma.go.jp/bosai/amedas/const/amedastable.json"
    response = requests.get(url)
    data = response.json()
    df2 = pd.DataFrame.from_dict(data, orient='index')
    df2.drop(columns=['type', 'elems', 'alt', 'enName'], inplace=True)
    df2[['lat1', 'lat2']] = pd.DataFrame(df2['lat'].tolist(), index=df2.index)
    df2[['lon1', 'lon2']] = pd.DataFrame(df2['lon'].tolist(), index=df2.index)
    df2['lat'] = df2['lat1'] + df2['lat2'] / 60
    df2['lon'] = df2['lon1'] + df2['lon2'] / 60
    df2.drop(columns=['lat1', 'lat2', 'lon1', 'lon2'], inplace=True)

    result = pd.concat([df2, df], axis=1)
    result = result.dropna(subset=["２４時間雨量"])

    colors = cm.hawaii_r(np.linspace(0, 1, 256))
    rgb_colors = (colors[:, :3] * 255).astype(int).tolist()

    min_height = 0
    max_height = 200
    result["color"] = result["２４時間雨量"].apply(
        lambda h: rgb_colors[int(255 * ((h - min_height) / (max_height - min_height)))]
    )

    return result

def main():
    st.title("10分間雨量")

    data = get_data()

    layer = pdk.Layer(
        "ColumnLayer",
        data=data,
        get_position=["lon", "lat"],
        get_elevation='２４時間雨量',
        elevation_scale=2500,
        radius=2500,
        elevation_range=[0, 500],
        get_fill_color='color',
        get_line_color=[0, 0, 0],
        pickable=True,
        auto_highlight=True,
        extruded=True,
    )

    tooltip = {
        "html": "地点名：<ruby>{kjName}<rt>{knName}</rt></ruby><br>気温：{気温}℃<br>10分間雨量：{１０分間雨量}mm<br>1時間雨量：{１時間雨量}mm<br>24時間雨量：{２４時間雨量}mm",
        "style": {"background": "grey", "color": "white", "font-family": '"ヒラギノ角ゴ Pro W3", "Meiryo", sans-serif', "z-index": "5000"},
    }

    view_state = pdk.ViewState(
        longitude=137.5936,
        latitude=36.047,
        zoom=5,
        min_zoom=1,
        max_zoom=15,
        pitch=50,
        bearing=-0
    )

    

    r = pdk.Deck(layer, tooltip=tooltip, initial_view_state=view_state)

    st.pydeck_chart(r)

if __name__ == "__main__":
    main()