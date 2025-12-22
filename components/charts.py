import json
from data.queries import get_order_accuracy_chart_data, get_timeliness_chart_data

# Функции для ECharts
def create_time_distribution_pie_echarts(work_minutes, idle_minutes):
    """Круговая диаграмма распределения времени"""
    total = work_minutes + idle_minutes
    if total == 0:
        work_percent = 0
        idle_percent = 0
    else:
        work_percent = round((work_minutes / total) * 100, 1)
        idle_percent = round((idle_minutes / total) * 100, 1)
    
    return {
        "title": {
            "text": "Распределение времени работы",
            "left": "center",
            "textStyle": {
                "fontSize": 14,
                "fontWeight": "bold",
                "color": "#333"
            }
        },
        "tooltip": {
            "trigger": "item",
            "formatter": "{a}<br/>{b}: {c} мин ({d}%)"
        },
        "legend": {
            "orient": "vertical",
            "left": "left",
            "top": "center",
            "textStyle": {"fontSize": 11}
        },
        "series": [{
            "name": "Распределение времени",
            "type": "pie",
            "radius": ["40%", "70%"],
            "center": ["50%", "50%"],
            "data": [
                {
                    "value": work_minutes, 
                    "name": f"Работа ({work_percent}%)", 
                    "itemStyle": {"color": "#4CAF50"}
                },
                {
                    "value": idle_minutes, 
                    "name": f"Простой ({idle_percent}%)", 
                    "itemStyle": {"color": "#F44336"}
                }
            ],
            "label": {
                "show": True,
                "formatter": "{b}: {d}%",
                "fontSize": 10
            },
            "emphasis": {
                "itemStyle": {
                    "shadowBlur": 10,
                    "shadowOffsetX": 0,
                    "shadowColor": "rgba(0, 0, 0, 0.5)"
                }
            },
            "animationDuration": 1000
        }]
    }

def create_idle_intervals_bar_echarts(idle_counts):
    """Столбчатая диаграмма периодов простоя"""
    interval_order = ['5-10 мин', '10-30 мин', '30-60 мин', '>1 часа']
    colors = ['#4CAF50', '#2196F3', '#FF9800', '#F44336']
    data = [idle_counts.get(k, 0) for k in interval_order]
    
    # Подготавливаем данные с информацией для кликов
    chart_data = []
    for i, (interval, value, color) in enumerate(zip(interval_order, data, colors)):
        chart_data.append({
            "name": interval,  # Это важно для получения имени при клике
            "value": value,
            "itemStyle": {"color": color}
        })
    
    return {
        "title": {
            "text": "Количество простоев по интервалам",
            "left": "center",
            "textStyle": {
                "fontSize": 14,
                "fontWeight": "bold",
                "color": "#333"
            }
        },
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"},
            "formatter": "{b}: {c} раз"
        },
        "xAxis": {
            "type": "category",
            "data": interval_order,
            "axisLine": {"show": True},
            "axisTick": {"show": True},
            "axisLabel": {"fontSize": 11}
        },
        "yAxis": {
            "type": "value",
            "name": "Количество простоев",
            "axisLine": {"show": True},
            "axisTick": {"show": True},
            "splitLine": {"show": True, "lineStyle": {"color": "#f0f0f0"}}
        },
        "series": [{
            "name": "Периоды простоя",
            "type": "bar",
            "data": chart_data,
            "label": {
                "show": True,
                "position": "top",
                "fontSize": 11,
                "fontWeight": "bold"
            },
            "itemStyle": {
                "borderRadius": [4, 4, 0, 0]
            },
            "barWidth": "60%",
            "emphasis": {
                "itemStyle": {
                    "shadowBlur": 10,
                    "shadowOffsetX": 0,
                    "shadowColor": "rgba(0, 0, 0, 0.5)"
                }
            }
        }],
        "grid": {
            "left": "5%",
            "right": "5%",
            "bottom": "15%",
            "top": "20%",
            "containLabel": True
        },
        # УБЕРИТЕ toolbox если не хотите кнопку сохранения
        # "toolbox": {
        #     "feature": {
        #         "saveAsImage": {}
        #     }
        # },
        "animationDuration": 800,
        "animationEasing": "cubicInOut"
    }

def create_order_accuracy_chart(start_date, end_date):
    """Создание диаграммы точности заказов"""
    
    chart_data = get_order_accuracy_chart_data(start_date, end_date)
    
    if not chart_data:
        return {
            "title": {
                "text": f"Точность заказов\n(за период {start_date} - {end_date})",
                "left": "center",
                "textStyle": {
                    "fontSize": 14,
                    "fontWeight": "bold",
                    "color": "#333"
                }
            },
            "tooltip": {
                "trigger": "item",
                "formatter": "Нет данных за выбранный период"
            },
            "xAxis": {"type": "category", "data": [], "show": False},
            "yAxis": {"type": "value", "show": False},
            "series": [{
                "type": "line",
                "data": [],
                "symbol": "none"
            }]
        }
    
    periods = [item['period'] for item in chart_data]
    accuracy_data = [item['accuracy'] for item in chart_data]
    
    # Создаем JavaScript функцию для форматирования тултипа
    tooltip_js = """
    function(params) {
        var dataIndex = params[0].dataIndex;
        var data = """ + json.dumps(chart_data) + """;
        var item = data[dataIndex];
        return params[0].name + '<br/>' +
               'Точность: ' + params[0].value.toFixed(1) + '%<br/>' +
               'Всего заказов: ' + item.total_orders + '<br/>' +
               'Без ошибок: ' + item.correct_orders + '<br/>' +
               'С ошибками: ' + item.error_orders;
    }
    """
    
    return {
        "title": {
            "text": f"Точность заказов\n(за период {start_date} - {end_date})",
            "left": "center",
            "textStyle": {
                "fontSize": 14,
                "fontWeight": "bold",
                "color": "#333"
            }
        },
        "tooltip": {
            "trigger": "axis",
            "formatter": tooltip_js
        },
        "xAxis": {
            "type": "category",
            "data": periods,
            "axisLine": {"show": True},
            "axisTick": {"show": True},
            "axisLabel": {"fontSize": 9, "rotate": 45}
        },
        "yAxis": {
            "type": "value",
            "min": 0,
            "max": 100,
            "axisLine": {"show": True},
            "axisTick": {"show": True},
            "splitLine": {"show": True, "lineStyle": {"color": "#f0f0f0"}},
            "axisLabel": {
                "formatter": "{value}%",
                "fontSize": 9
            }
        },
        "series": [{
            "name": "Точность заказов",
            "type": "line",
            "data": accuracy_data,
            "lineStyle": {"color": "#4CAF50", "width": 3},
            "itemStyle": {"color": "#4CAF50"},
            "smooth": True,
            "symbol": "circle",
            "symbolSize": 6,
            "areaStyle": {
                "color": {
                    "type": "linear",
                    "x": 0,
                    "y": 0,
                    "x2": 0,
                    "y2": 1,
                    "colorStops": [
                        {"offset": 0, "color": "rgba(76, 175, 80, 0.6)"},
                        {"offset": 1, "color": "rgba(76, 175, 80, 0.1)"}
                    ]
                }
            }
        }],
        "grid": {
            "left": "5%",
            "right": "5%",
            "bottom": "20%",
            "top": "20%",
            "containLabel": True
        },
        "animationDuration": 1000,
        "animationEasing": "cubicInOut"
    }

def create_problematic_hours_chart(problematic_hours):
    """Создание диаграммы проблемных часов"""
    
    if not problematic_hours:
        return {
            "title": {
                "text": "Топ-5 проблемных часов",
                "left": "center",
                "textStyle": {
                    "fontSize": 14,
                    "fontWeight": "bold",
                    "color": "#333"
                }
            },
            "tooltip": {
                "trigger": "item",
                "formatter": "Нет данных за выбранный период"
            },
            "xAxis": {"type": "category", "data": [], "show": False},
            "yAxis": {"type": "value", "show": False},
            "series": []
        }
    
    hours = [f"{item['hour']}:00" for item in problematic_hours]
    delay_percentages = [item['delay_percentage'] for item in problematic_hours]
    delayed_counts = [item['delayed_orders'] for item in problematic_hours]
    total_counts = [item['total_orders'] for item in problematic_hours]
    
    # Создаем ВНЕШНЮЮ JavaScript функцию
    tooltip_js = """
    function(params) {
        var dataIndex = params[0].dataIndex;
        var hour = params[0].name;
        var delayed = """ + str(delayed_counts) + """[dataIndex];
        var total = """ + str(total_counts) + """[dataIndex];
        var percent = params[0].value;
        
        return hour + '<br/>' +
               'Процент просрочек: ' + percent.toFixed(1) + '%<br/>' +
               'Просрочено: ' + delayed + ' заказов<br/>' +
               'Всего: ' + total + ' заказов';
    }
    """
    
    return {
        "title": {
            "text": "Топ-5 проблемных часов",
            "left": "center",
            "textStyle": {
                "fontSize": 14,
                "fontWeight": "bold",
                "color": "#333"
            }
        },
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"},
            "formatter": tooltip_js
        },
        "xAxis": {
            "type": "category",
            "data": hours,
            "axisLine": {"show": True},
            "axisTick": {"show": True},
            "axisLabel": {"fontSize": 11, "rotate": 0}
        },
        "yAxis": {
            "type": "value",
            "name": "% просрочек",
            "min": 0,
            "max": 100,
            "axisLine": {"show": True},
            "axisTick": {"show": True},
            "splitLine": {"show": True, "lineStyle": {"color": "#f0f0f0"}},
            "axisLabel": {
                "formatter": "{value}%",
                "fontSize": 9,
                "margin": 2
            },
            "nameTextStyle": {
                "fontSize": 10,
                "padding": [0, 0, 0, 5]
            }
        },
        "series": [{
            "name": "Процент просрочек",
            "type": "bar",
            "data": delay_percentages,
            "itemStyle": {
                "color": {
                    "type": "linear",
                    "x": 0,
                    "y": 0,
                    "x2": 0,
                    "y2": 1,
                    "colorStops": [
                        {"offset": 0, "color": "#F44336"},
                        {"offset": 1, "color": "#FF9800"}
                    ]
                }
            },
            "label": {
                "show": True,
                "position": "top",
                "formatter": "{c}%",
                "fontSize": 10,
                "fontWeight": "bold"
            },
            "barWidth": "60%"
        }],
        "grid": {
            "left": "10%",
            "right": "5%",
            "bottom": "15%",
            "top": "20%",
            "containLabel": True
        },
        "animationDuration": 1000,
        "animationEasing": "cubicInOut"
    }

def create_error_hours_chart(error_hours):
    """Создание диаграммы часов с ошибками"""
    
    print(f"DEBUG [create_error_hours_chart]: Получены данные: {len(error_hours) if error_hours else 0} записей")
    
    if not error_hours:
        print("DEBUG: Нет данных для диаграммы часов с ошибками - показываем заглушку")
        return {
            "title": {
                "text": "Топ-5 часов с ошибками",
                "subtext": "Нет данных об ошибках за выбранный период",
                "left": "center",
                "textStyle": {
                    "fontSize": 14,
                    "fontWeight": "bold",
                    "color": "#333"
                },
                "subtextStyle": {
                    "fontSize": 12,
                    "color": "#666"
                }
            },
            "tooltip": {
                "trigger": "item",
                "formatter": "Нет данных об ошибках за выбранный период"
            },
            "graphic": {
                "type": "text",
                "left": "center",
                "top": "middle",
                "style": {
                    "text": "Нет данных",
                    "fontSize": 16,
                    "fontWeight": "bold",
                    "fill": "#999"
                }
            },
            "xAxis": {"type": "category", "data": [], "show": False},
            "yAxis": {"type": "value", "show": False},
            "series": []
        }
    
    hours = [f"{item['hour']}:00" for item in error_hours]
    error_percentages = [item['error_percentage'] for item in error_hours]
    error_counts = [item['error_orders_count'] for item in error_hours]
    total_counts = [item['total_orders_in_hour'] for item in error_hours]
    error_types = [item['error_types'] for item in error_hours]
    
    print(f"DEBUG: Часы: {hours}")
    print(f"DEBUG: Проценты ошибок: {error_percentages}")
    print(f"DEBUG: Количество ошибок: {error_counts}")
    print(f"DEBUG: Всего заказов: {total_counts}")
    
    # Создаем JavaScript функцию для форматирования тултипа
    tooltip_js = """
    function(params) {
        var dataIndex = params.dataIndex || 0;
        var hour = """ + json.dumps(hours) + """[dataIndex];
        var errors = """ + json.dumps(error_counts) + """[dataIndex];
        var total = """ + json.dumps(total_counts) + """[dataIndex];
        var percent = """ + json.dumps(error_percentages) + """[dataIndex];
        var types = """ + json.dumps(error_types) + """[dataIndex];
        
        var tooltip = hour + '<br/>' +
                      '<b>Процент ошибок:</b> ' + percent.toFixed(1) + '%<br/>' +
                      '<b>С ошибками:</b> ' + errors + ' заказов<br/>' +
                      '<b>Всего заказов:</b> ' + total;
        
        if (types && types !== '') {
            tooltip += '<br/><b>Типы ошибок:</b> ' + types;
        }
        
        return tooltip;
    }
    """
    
    return {
        "title": {
            "text": "Топ-5 часов с ошибками",
            "left": "center",
            "textStyle": {
                "fontSize": 14,
                "fontWeight": "bold",
                "color": "#333"
            }
        },
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"},
            "formatter": tooltip_js,
            "backgroundColor": "rgba(50, 50, 50, 0.7)",
            "borderColor": "#333",
            "textStyle": {"color": "#fff"}
        },
        "xAxis": {
            "type": "category",
            "data": hours,
            "axisLine": {"show": True, "lineStyle": {"color": "#333"}},
            "axisTick": {"show": True},
            "axisLabel": {
                "fontSize": 11,
                "rotate": 0,
                "color": "#333"
            },
            "name": "Час дня",
            "nameLocation": "middle",
            "nameGap": 25
        },
        "yAxis": {
            "type": "value",
            "name": "Процент ошибок (%)",
            "min": 0,
            "max": 100,
            "axisLine": {"show": True, "lineStyle": {"color": "#333"}},
            "axisTick": {"show": True},
            "splitLine": {
                "show": True, 
                "lineStyle": {
                    "color": "#f0f0f0",
                    "type": "dashed"
                }
            },
            "axisLabel": {
                "formatter": "{value}%",
                "fontSize": 9,
                "color": "#333"
            },
            "nameTextStyle": {
                "fontSize": 10,
                "padding": [0, 0, 0, 10]
            }
        },
        "series": [{
            "name": "Процент ошибок",
            "type": "bar",
            "data": error_percentages,
            "itemStyle": {
                "color": {
                    "type": "linear",
                    "x": 0,
                    "y": 0,
                    "x2": 0,
                    "y2": 1,
                    "colorStops": [
                        {"offset": 0, "color": "#9C27B0"},
                        {"offset": 0.5, "color": "#673AB7"},
                        {"offset": 1, "color": "#3F51B5"}
                    ]
                },
                "borderRadius": [4, 4, 0, 0],
                "shadowBlur": 5,
                "shadowColor": "rgba(0, 0, 0, 0.2)",
                "shadowOffsetY": 2
            },
            "label": {
                "show": True,
                "position": "top",
                "formatter": "{c}%",
                "fontSize": 10,
                "fontWeight": "bold",
                "color": "#333"
            },
            "barWidth": "50%",
            "emphasis": {
                "itemStyle": {
                    "shadowBlur": 10,
                    "shadowColor": "rgba(0, 0, 0, 0.3)"
                }
            }
        }],
        "grid": {
            "left": "10%",
            "right": "10%",
            "bottom": "20%",
            "top": "20%",
            "containLabel": True,
            "backgroundColor": "#fafafa"
        },
        "animationDuration": 1000,
        "animationEasing": "cubicInOut"
    }

def create_timeliness_chart(chart_data, chart_type='timely'):
    """Создание диаграмм своевременности"""
    
    if not chart_data:
        return {
            "title": {
                "text": "Нет данных за выбранный период",
                "left": "center",
                "textStyle": {"color": "#666"}
            },
            "xAxis": {"type": "category", "data": [], "show": False},
            "yAxis": {"type": "value", "show": False},
            "series": []
        }
    
    periods = [item['period'] for item in chart_data]
    delivery_data = [item['Доставка_клиенту_с_РЦ'] for item in chart_data]
    rc_data = [item['РЦ'] for item in chart_data]
    
    title = "Своевременность заказов Клиент" if chart_type == 'timely' else "Просроченные заказы Клиент"
    delivery_name = "Доставка клиенту с РЦ" if chart_type == 'timely' else "Доставка клиенту с РЦ"
    rc_name = "РЦ" if chart_type == 'timely' else "РЦ"
    delivery_color = "rgb(33, 150, 243)" if chart_type == 'timely' else "#F44336"
    rc_color = "#4CAF50" if chart_type == 'timely' else "#FF9800"
    
    return {
        "title": {
            "text": title,
            "left": "center",
            "textStyle": {
                "fontSize": 12,
                "fontWeight": "bold",
                "color": "#333"
            }
        },
        "tooltip": {
            "trigger": "axis",
            "formatter": """function(params) {
                var result = params[0].name + '<br/>';
                for (var i = 0; i < params.length; i++) {
                    result += params[i].seriesName + ': ' + params[i].value + ' заказов<br/>';
                }
                return result;
            }"""
        },
        "xAxis": {
            "type": "category",
            "boundaryGap": False,
            "data": periods,
            "axisLine": {"show": True},
            "axisTick": {"show": True},
            "axisLabel": {"fontSize": 9, "rotate": 45}
        },
        "yAxis": {
            "type": "value",
            "min": 0,
            "axisLine": {"show": True},
            "axisTick": {"show": True},
            "splitLine": {"show": True, "lineStyle": {"color": "#f0f0f0"}},
            "axisLabel": {"formatter": "{value}", "fontSize": 9}
        },
        "series": [
            {
                "name": delivery_name,
                "data": delivery_data,
                "type": "line",
                "areaStyle": {
                    "color": {
                        "type": "linear",
                        "x": 0,
                        "y": 0,
                        "x2": 0,
                        "y2": 1,
                        "colorStops": [
                            {"offset": 0, "color": "rgba(33, 150, 243, 0.6)"} if chart_type == 'timely' else {"offset": 0, "color": "rgba(244, 67, 54, 0.6)"},
                            {"offset": 1, "color": "rgba(33, 150, 243, 0.1)"} if chart_type == 'timely' else {"offset": 1, "color": "rgba(244, 67, 54, 0.1)"}
                        ]
                    }
                },
                "lineStyle": {"color": delivery_color, "width": 2},
                "itemStyle": {"color": delivery_color},
                "smooth": True,
                "symbol": "circle",
                "symbolSize": 4
            },
            {
                "name": rc_name,
                "data": rc_data,
                "type": "line",
                "areaStyle": {
                    "color": {
                        "type": "linear",
                        "x": 0,
                        "y": 0,
                        "x2": 0,
                        "y2": 1,
                        "colorStops": [
                            {"offset": 0, "color": "rgba(76, 175, 80, 0.6)"},
                            {"offset": 1, "color": "rgba(76, 175, 80, 0.1)"}
                        ]
                    }
                },
                "lineStyle": {"color": rc_color, "width": 2},
                "itemStyle": {"color": rc_color},
                "smooth": True,
                "symbol": "circle",
                "symbolSize": 4
            }
        ],
        "grid": {
            "left": "5%",
            "right": "5%",
            "bottom": "20%",
            "top": "20%",
            "containLabel": True
        },
        "animationDuration": 1000,
        "animationEasing": "cubicInOut"
    }

def create_operations_type_chart(employee_name, operations_detail):
    colors = [
        '#0D2B4F', '#11345C', '#153D69', '#194676', '#1D4F83',
        '#215890', '#25619D', '#296AAA', '#2D73B7', '#317CC4',
        '#4A8BC9', '#6399CF', '#7CA8D5', '#95B7DB', '#AEC6E1'
    ]
    
    categories = list(operations_detail.keys())[:15]
    values = [operations_detail.get(k, 0) for k in categories]
    
    if not categories or sum(values) == 0:
        categories = ["Нет данных"]
        values = [1]
    
    return {
        "title": {
            "text": "Распределение операций по типам",
            "left": "center",
            "textStyle": {
                "fontSize": 12,
                "fontWeight": "bold",
                "color": "#333"
            }
        },
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"},
            "formatter": "{a}<br/>{b}: {c} операций"
        },
        "xAxis": {
            "type": "category",
            "data": categories,
            "axisLabel": {
                "rotate": 45,
                "fontSize": 8,
                "interval": 0
            }
        },
        "yAxis": {
            "type": "value",
            "name": "Количество операций",
            "nameLocation": "middle",
            "nameGap": 30
        },
        "series": [{
            "name": "Операции",
            "type": "bar",
            "data": [{"value": v, "itemStyle": {"color": colors[i % len(colors)]}} 
                    for i, v in enumerate(values)],
            "label": {
                "show": True,
                "position": "top",
                "fontSize": 8
            },
            "itemStyle": {
                "borderRadius": [4, 4, 0, 0]
            }
        }],
        "grid": {
            "left": "3%",
            "right": "4%",
            "bottom": "25%",
            "top": "20%",
            "containLabel": True
        },
        "animationDuration": 600,
        "animationEasing": "cubicInOut"
    }

def create_fines_pie_chart(category_data):
    data = []
    colors = [
        '#B71C1C', '#C62828', '#D32F2F', '#E53935', '#F44336',
        '#EF5350', '#E57373', '#EF9A9A', '#FFCDD2', '#FFEBEE'
    ]
    
    for i, (category, stats) in enumerate(category_data.items()):
        if stats['count'] > 0:
            data.append({
                "name": category[:20],
                "value": stats['count'],
                "itemStyle": {"color": colors[i % len(colors)]}
            })
    
    if not data:
        data.append({
            "name": "Нет данных",
            "value": 1,
            "itemStyle": {"color": "#CCCCCC"}
        })
    
    return {
        "title": {
            "text": "Распределение штрафов по категориям",
            "left": "center",
            "textStyle": {
                "fontSize": 14,
                "fontWeight": "bold",
                "color": "#333"
            }
        },
        "tooltip": {
            "trigger": "item",
            "formatter": "{a}<br/>{b}: {c} шт ({d}%)"
        },
        "legend": {
            "orient": "vertical",
            "left": "left",
            "top": "center",
            "textStyle": {"fontSize": 9},
            "itemHeight": 8,
            "itemWidth": 8
        },
        "series": [{
            "name": "Штрафы по категориям",
            "type": "pie",
            "radius": ["40%", "70%"],
            "center": ["60%", "50%"],
            "avoidLabelOverlap": True,
            "itemStyle": {
                "borderRadius": 6,
                "borderColor": "#fff",
                "borderWidth": 2
            },
            "label": {
                "show": True,
                "formatter": "{b}: {d}%",
                "fontSize": 8
            },
            "emphasis": {
                "itemStyle": {
                    "shadowBlur": 10,
                    "shadowOffsetX": 0,
                    "shadowColor": "rgba(0, 0, 0, 0.5)"
                },
                "label": {
                    "show": True,
                    "fontSize": 10,
                    "fontWeight": "bold"
                }
            },
            "labelLine": {"show": True},
            "data": data,
            "animationType": "scale",
            "animationEasing": "elasticOut"
        }],
        "animationDuration": 1500,
        "animationEasing": "cubicInOut"
    }

def create_fines_amount_bar_chart(category_data):
    categories = []
    amounts = []
    colors = [
        '#B71C1C', '#C62828', '#D32F2F', '#E53935', '#F44336',
        '#EF5350', '#E57373', '#EF9A9A', '#FFCDD2'
    ]
    
    for i, (category, stats) in enumerate(category_data.items()):
        if stats['total_amount'] > 0:
            categories.append(category[:15])
            amounts.append({
                "value": stats['total_amount'],
                "itemStyle": {"color": colors[i % len(colors)]}
            })
    
    if not categories:
        categories = ["Нет данных"]
        amounts = [{"value": 1, "itemStyle": {"color": "#CCCCCC"}}]
    
    return {
        "title": {
            "text": "Сумма штрафов по категориям",
            "left": "center",
            "textStyle": {
                "fontSize": 14,
                "fontWeight": "bold",
                "color": "#333"
            }
        },
        "tooltip": {
            "trigger": "axis",
            "formatter": "{a}<br/>{b}: {c} руб."
        },
        "xAxis": {
            "type": "category",
            "data": categories,
            "axisLine": {"show": True},
            "axisTick": {"show": True},
            "axisLabel": {
                "rotate": 45,
                "fontSize": 8,
                "interval": 0
            }
        },
        "yAxis": {
            "type": "value",
            "name": "Сумма, руб.",
            "axisLine": {"show": True},
            "axisTick": {"show": True},
            "splitLine": {"show": True, "lineStyle": {"color": "#f0f0f0"}},
            "axisLabel": {"formatter": "{value}", "fontSize": 9}
        },
        "series": [{
            "name": "Сумма штрафов",
            "type": "bar",
            "data": amounts,
            "label": {
                "show": True,
                "position": "top",
                "formatter": "{c} руб.",
                "fontSize": 8
            },
            "itemStyle": {
                "borderRadius": [4, 4, 0, 0]
            }
        }],
        "grid": {
            "left": "5%",
            "right": "5%",
            "bottom": "30%",
            "top": "20%",
            "containLabel": True
        },
        "animationDuration": 1000,
        "animationEasing": "cubicInOut"
    }

def create_employee_fines_chart(employee_data):
    category_counts = {}
    category_amounts = {}
    
    for fine in employee_data.get('Штрафы', []):
        category = fine.get('category', 'Неизвестно')
        amount = fine.get('amount', 0)
        
        if category not in category_counts:
            category_counts[category] = 0
            category_amounts[category] = 0
        
        category_counts[category] += 1
        category_amounts[category] += amount
    
    data = []
    colors = [
        '#B71C1C', '#C62828', '#D32F2F', '#E53935', '#F44336',
        '#EF5350', '#E57373', '#EF9A9A', '#FFCDD2'
    ]
    
    total_fines = employee_data.get('Количество_штрафов', 0)
    
    for i, (category, count) in enumerate(category_counts.items()):
        amount = category_amounts.get(category, 0)
        percentage = (count / total_fines * 100) if total_fines > 0 else 0
        
        data.append({
            "name": f"{category[:15]}",
            "value": count,
            "itemStyle": {"color": colors[i % len(colors)]},
            "amount": amount
        })
    
    if not data:
        data.append({
            "name": "Нет штрафов",
            "value": 1,
            "itemStyle": {"color": "#CCCCCC"},
            "amount": 0
        })
    
    return {
        "title": {
            "text": f"Штрафы: {employee_data.get('Сотрудник', 'Сотрудник')}",
            "left": "center",
            "textStyle": {
                "fontSize": 16,
                "fontWeight": "bold",
                "color": "#333"
            }
        },
        "tooltip": {
            "trigger": "item",
            "formatter": "{a}<br/>{b}: {c} шт ({d}%)<br/>Сумма: {amount} руб"
        },
        "legend": {
            "orient": "vertical",
            "left": "left",
            "top": "center",
            "textStyle": {"fontSize": 10},
            "itemHeight": 8,
            "itemWidth": 8
        },
        "series": [{
            "name": "Штрафы сотрудника",
            "type": "pie",
            "radius": ["40%", "70%"],
            "center": ["60%", "50%"],
            "avoidLabelOverlap": True,
            "itemStyle": {
                "borderRadius": 6,
                "borderColor": "#fff",
                "borderWidth": 2
            },
            "label": {
                "show": True,
                "formatter": "{b}\n{d}%",
                "fontSize": 9,
                "overflow": "break"
            },
            "emphasis": {
                "itemStyle": {
                    "shadowBlur": 10,
                    "shadowOffsetX": 0,
                    "shadowColor": "rgba(0, 0, 0, 0.5)"
                },
                "label": {
                    "show": True,
                    "fontSize": 11,
                    "fontWeight": "bold"
                }
            },
            "labelLine": {
                "show": True,
                "length": 10,
                "length2": 5
            },
            "data": data,
            "animationType": "scale",
            "animationEasing": "elasticOut"
        }],
        "animationDuration": 1500,
        "animationEasing": "cubicInOut"
    }

def create_timeline_chart(employee_name, selected_day, selected_interval):
    """Создание timeline-диаграммы для отображения простоев в течение дня"""
    
    # Генерация тестовых данных
    import random
    from datetime import datetime, timedelta
    
    # Если нет выбранного дня, используем сегодня
    if not selected_day:
        selected_day = datetime.now().strftime('%Y-%m-%d')
    
    # Генерация тестовых интервалов работы и простоев
    intervals = []
    colors = {
        'Работа': '#4CAF50',
        'Простой 5-10 мин': '#FF9800',
        'Простой 10-30 мин': '#FF5722',
        'Простой 30-60 мин': '#E91E63',
        'Простой >1 часа': '#9C27B0'
    }
    
    # Создаем рабочий день 8:00 - 17:00
    work_start = 8.0  # 8:00
    work_end = 17.0   # 17:00
    
    # Добавляем рабочие периоды
    current_time = work_start
    while current_time < work_end:
        # Длительность работы (1-3 часа)
        work_duration = random.uniform(1.0, 3.0)
        if current_time + work_duration > work_end:
            work_duration = work_end - current_time
        
        intervals.append({
            'name': 'Работа',
            'start': current_time,
            'end': current_time + work_duration,
            'color': colors['Работа']
        })
        
        current_time += work_duration
        
        # Добавляем простой (если еще не конец дня)
        if current_time < work_end:
            # Выбираем тип простоя на основе selected_interval
            if selected_interval == '5-10 мин':
                idle_duration = random.uniform(5/60, 10/60)  # 5-10 минут в часах
                idle_type = 'Простой 5-10 мин'
            elif selected_interval == '10-30 мин':
                idle_duration = random.uniform(10/60, 30/60)  # 10-30 минут
                idle_type = 'Простой 10-30 мин'
            elif selected_interval == '30-60 мин':
                idle_duration = random.uniform(30/60, 60/60)  # 30-60 минут
                idle_type = 'Простой 30-60 мин'
            else:  # >1 часа или по умолчанию
                idle_duration = random.uniform(60/60, 120/60)  # 1-2 часа
                idle_type = 'Простой >1 часа'
            
            if current_time + idle_duration > work_end:
                idle_duration = work_end - current_time
            
            intervals.append({
                'name': idle_type,
                'start': current_time,
                'end': current_time + idle_duration,
                'color': colors.get(idle_type, '#607D8B')
            })
            
            current_time += idle_duration
    
    # Подготовка данных для ECharts
    data = []
    for i, interval in enumerate(intervals):
        data.append({
            'value': [interval['start'], i, interval['end'], i],
            'itemStyle': {'color': interval['color']},
            'name': interval['name']
        })
    
    # Создаем легенду
    legend_data = list(set([interval['name'] for interval in intervals]))
    
    # Исправленный тултип - используем строку с JavaScript кодом
    tooltip_formatter = """
    function(params) {
        var start = params.data.value[0];
        var end = params.data.value[2];
        var duration = end - start;
        return params.data.name + '<br/>' +
               'Начало: ' + start.toFixed(2) + ':00<br/>' +
               'Конец: ' + end.toFixed(2) + ':00<br/>' +
               'Длительность: ' + duration.toFixed(2) + ' часов';
    }
    """
    
    # Исправленный renderItem для custom-серии
    render_item_js = """
    function(params, api) {
        var xValue = api.value(0);
        var yValue = api.value(1);
        var xValue2 = api.value(2);
        
        var start = api.coord([xValue, yValue]);
        var end = api.coord([xValue2, yValue]);
        
        var height = api.size([0, 1])[1] * 0.6;
        
        return {
            type: 'rect',
            shape: {
                x: start[0],
                y: start[1] - height / 2,
                width: end[0] - start[0],
                height: height
            },
            style: api.style({fill: api.visual('color')})
        };
    }
    """
    
    return {
        "title": {
            "text": f"Распределение времени за {selected_day}",
            "left": "center",
            "textStyle": {
                "fontSize": 16,
                "fontWeight": "bold",
                "color": "#333"
            }
        },
        "tooltip": {
            "trigger": "item",
            "formatter": tooltip_formatter
        },
        "legend": {
            "data": legend_data,
            "top": "30px",
            "textStyle": {"fontSize": 12}
        },
        "xAxis": {
            "type": "value",
            "name": "Время суток (часы)",
            "min": 0,
            "max": 24,
            "interval": 2,
            "axisLine": {"show": True},
            "axisTick": {"show": True},
            "splitLine": {"show": True},
            "axisLabel": {
                "formatter": "{value}:00",
                "fontSize": 10
            }
        },
        "yAxis": {
            "type": "category",
            "data": [f"Период {i+1}" for i in range(len(intervals))],
            "axisLine": {"show": True},
            "axisTick": {"show": True},
            "axisLabel": {"fontSize": 10}
        },
        "series": [{
            "type": "custom",
            "renderItem": render_item_js,
            "data": data,
            "encode": {
                "x": [0, 2],  # start и end по оси X
                "y": 1        # индекс по оси Y
            }
        }],
        "grid": {
            "left": "5%",
            "right": "5%",
            "bottom": "10%",
            "top": "20%",
            "containLabel": True
        },
        "animationDuration": 1000
    }

def create_empty_pie_chart(summary_data, filters=None):
    """
    Диаграмма 1: Доля пустых ячеек
    Показывает: Кол.МХ (все) vs Кол.Пустых МХ (пустые)
    """
    total = summary_data.get('total', 0)
    empty = summary_data.get('empty', 0)
    occupied = summary_data.get('occupied', 0)
    
    # Цвета
    colors = ['#2196F3', '#0D47A1']
    
    # Данные для диаграммы
    data = []
    if total > 0:
        empty_percent = round((empty / total) * 100, 1)
        occupied_percent = round((occupied / total) * 100, 1)
        
        data = [
            {
                "name": f"Пустые ({empty_percent}%)",
                "value": empty,
                "itemStyle": {"color": colors[0]}
            },
            {
                "name": f"Занятые ({occupied_percent}%)",
                "value": occupied,
                "itemStyle": {"color": colors[1]}
            }
        ]
        
        # Легенда
        legend_data = [
            {"name": f"Пустые ({empty_percent}%)", "icon": "circle"},
            {"name": f"Занятые ({occupied_percent}%)", "icon": "circle"}
        ]
    else:
        data = [{"name": "Нет данных", "value": 1, "itemStyle": {"color": "#CCCCCC"}}]
        legend_data = [{"name": "Нет данных", "icon": "circle"}]
    
    # Заголовок с информацией о фильтрах
    title_text = "Доля пустых ячеек"
    if filters:
        active_filters = []
        for key, value in filters.items():
            if value and value != 'Все':
                active_filters.append(f"{value}")
        if active_filters:
            title_text += f"\nФильтры: {', '.join(active_filters[:3])}"
            if len(active_filters) > 3:
                title_text += "..."
    
    return {
        "title": {
            "text": title_text,
            "left": "center",
            "textStyle": {
                "fontSize": 14,
                "fontWeight": "bold",
                "color": "#333"
            }
        },
        "tooltip": {
            "trigger": "item",
            "formatter": "{a}<br/>{b}: {c} ячеек"
        },
        "legend": {
            "data": [item["name"] for item in legend_data],
            "orient": "horizontal",
            "bottom": 0,
            "left": "center",
            "textStyle": {"fontSize": 10},
            "itemHeight": 8,
            "itemWidth": 8
        },
        "series": [{
            "name": "Статус ячеек",
            "type": "pie",
            "radius": ["40%", "70%"],
            "center": ["50%", "45%"],
            "avoidLabelOverlap": True,
            "itemStyle": {
                "borderRadius": 6,
                "borderColor": "#fff",
                "borderWidth": 2
            },
            "label": {
                "show": True,
                "formatter": "{b}: {d}%",
                "fontSize": 10
            },
            "emphasis": {
                "itemStyle": {
                    "shadowBlur": 10,
                    "shadowOffsetX": 0,
                    "shadowColor": "rgba(0, 0, 0, 0.5)"
                }
            },
            "labelLine": {"show": True},
            "data": data
        }],
        "animationDuration": 1000
    }

def create_types_pie_chart(chart_data, filters=None):
    """
    Диаграмма 2: Доли типов ячеек
    Показывает доли каждого Типа МХ (location_type)
    """
    types_data = chart_data.get('by_location_type', [])
    
    # УБИРАЕМ ОГРАНИЧЕНИЕ на количество типов
    # types_data = types_data[:10]  # УДАЛИТЬ ЭТУ СТРОКУ
    
    # Цвета в синих оттенках
    colors = [
        '#1A237E', '#283593', '#303F9F', '#3949AB', '#3F51B5',
        '#5C6BC0', '#7986CB', '#9FA8DA', '#C5CAE9', '#E8EAF6',
        '#0D47A1', '#1565C0', '#1976D2', '#1E88E5', '#2196F3',
        '#64B5F6', '#90CAF9', '#BBDEFB', '#E3F2FD', '#F5F5F5'
    ]
    
    # Подготавливаем данные
    data = []
    total_all = sum(item['total'] for item in types_data)
    
    for i, item in enumerate(types_data):  # УБРАЛИ [:10]
        loc_type = item['location_type']
        if len(loc_type) > 15:
            display_name = loc_type[:15] + "..."
        else:
            display_name = loc_type
            
        total = item['total']
        percentage = round((total / total_all) * 100, 1) if total_all > 0 else 0
        
        data.append({
            "name": f"{display_name} ({percentage}%)",
            "value": total,
            "itemStyle": {"color": colors[i % len(colors)]},
            "original_name": loc_type,
            "percentage": percentage
        })
    
    if not data:
        data.append({
            "name": "Нет данных",
            "value": 1,
            "itemStyle": {"color": "#CCCCCC"},
            "original_name": "Нет данных",
            "percentage": 0
        })
    
    # Создаем легенду
    legend_data = []
    for item in data[:15]:  # В легенде показываем только топ-15
        legend_data.append(item["name"])
    
    # Заголовок с информацией о фильтрах
    title_text = "Доли типов ячеек"
    if filters:
        active_filters = []
        for key, value in filters.items():
            if value and value != 'Все':
                active_filters.append(f"{value}")
        if active_filters:
            title_text += f"\nФильтры: {', '.join(active_filters[:3])}"
            if len(active_filters) > 3:
                title_text += "..."
    
    # Простой тултип без JavaScript
    return {
        "title": {
            "text": title_text,
            "left": "center",
            "textStyle": {
                "fontSize": 14,
                "fontWeight": "bold",
                "color": "#333"
            }
        },
        "tooltip": {
            "trigger": "item",
            "formatter": "{a}<br/>{b}: {c} ячеек ({d}%)"
        },
        "legend": {
            "data": legend_data,
            "orient": "vertical",
            "right": 10,
            "top": "middle",
            "textStyle": {"fontSize": 8},
            "itemHeight": 8,
            "itemWidth": 8,
            "type": "scroll"  # Добавляем прокрутку если много элементов
        },
        "series": [{
            "name": "Типы ячеек",
            "type": "pie",
            "radius": ["40%", "70%"],
            "center": ["40%", "50%"],  # Сдвигаем влево чтобы легенда поместилась
            "avoidLabelOverlap": True,
            "itemStyle": {
                "borderRadius": 6,
                "borderColor": "#fff",
                "borderWidth": 2
            },
            "label": {
                "show": True,
                "formatter": "{b}",
                "fontSize": 8
            },
            "emphasis": {
                "itemStyle": {
                    "shadowBlur": 10,
                    "shadowOffsetX": 0,
                    "shadowColor": "rgba(0, 0, 0, 0.5)"
                }
            },
            "labelLine": {
                "show": True,
                "length": 10,
                "length2": 5
            },
            "data": data
        }],
        "animationDuration": 1000
    }

def create_types_bar_chart(chart_data, filters=None):
    """
    Диаграмма 3: Количество типов ячеек
    Ось X: Типы МХ (location_type)
    Ряды: Всего МХ и Пустые МХ
    """
    types_data = chart_data.get('by_location_type', [])
    
    # УБИРАЕМ ОГРАНИЧЕНИЕ на количество типов
    # types_data = types_data[:10]  # УДАЛИТЬ ЭТУ СТРОКУ
    
    # Цвета
    total_color = '#0D47A1'    # Темно-синий для "Всего МХ"
    empty_color = '#2196F3'    # Светло-синий для "Пустые МХ"
    
    # Подготавливаем данные
    categories = []
    total_values = []
    empty_values = []
    
    for item in types_data:  # УБРАЛИ [:10]
        loc_type = item['location_type']
        if len(loc_type) > 12:
            display_name = loc_type[:12] + "..."
        else:
            display_name = loc_type
            
        categories.append(display_name)
        total_values.append({
            "value": item['total'],
            "itemStyle": {"color": total_color}
        })
        empty_values.append({
            "value": item['empty'],
            "itemStyle": {"color": empty_color}
        })
    
    if not categories:
        categories = ["Нет данных"]
        total_values = [{"value": 1, "itemStyle": {"color": total_color}}]
        empty_values = [{"value": 0, "itemStyle": {"color": empty_color}}]
    
    # Заголовок с информацией о фильтрах
    title_text = "Количество типов ячеек"
    if filters:
        active_filters = []
        for key, value in filters.items():
            if value and value != 'Все':
                active_filters.append(f"{value}")
        if active_filters:
            title_text += f"\nФильтры: {', '.join(active_filters[:3])}"
            if len(active_filters) > 3:
                title_text += "..."
    
    # Простой тултип без JavaScript
    return {
        "title": {
            "text": title_text,
            "left": "center",
            "textStyle": {
                "fontSize": 14,
                "fontWeight": "bold",
                "color": "#333"
            }
        },
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"},
            "formatter": "{b}<br/>{a0}: {c0} ячеек<br/>{a1}: {c1} ячеек"
        },
        "legend": {
            "data": ['Всего МХ', 'Пустые МХ'],
            "top": "30px",
            "textStyle": {"fontSize": 11}
        },
        "xAxis": {
            "type": "category",
            "data": categories,
            "axisLine": {"show": True},
            "axisTick": {"show": True},
            "axisLabel": {
                "rotate": 45,
                "fontSize": 9,
                "interval": 0  # Показывать все метки
            }
        },
        "yAxis": {
            "type": "value",
            "name": "Количество ячеек",
            "axisLine": {"show": True},
            "axisTick": {"show": True},
            "splitLine": {"show": True, "lineStyle": {"color": "#f0f0f0"}},
            "axisLabel": {"formatter": "{value}", "fontSize": 9}
        },
        "series": [
            {
                "name": "Всего МХ",
                "type": "bar",
                "data": total_values,
                "itemStyle": {
                    "borderRadius": [4, 4, 0, 0]
                },
                "label": {
                    "show": True,
                    "position": "top",
                    "formatter": "{c}",
                    "fontSize": 8
                }
            },
            {
                "name": "Пустые МХ",
                "type": "bar",
                "data": empty_values,
                "itemStyle": {
                    "borderRadius": [4, 4, 0, 0]
                },
                "label": {
                    "show": True,
                    "position": "top",
                    "formatter": "{c}",
                    "fontSize": 8
                }
            }
        ],
        "grid": {
            "left": "5%",
            "right": "5%",
            "bottom": "25%",
            "top": "20%",
            "containLabel": True
        },
        "animationDuration": 1000
    }