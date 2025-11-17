import pandas as pd

from src.dashboard import build_patient_options
from src.main import build_scatter_figure


def test_build_patient_options_returns_unique_ids():
    df = pd.DataFrame({
        'ID': [1, 1, 2],
        'Возраст': [30, 31, 45],
        'Пол': ['M', 'M', 'F']
    })

    options = build_patient_options(df)

    assert len(options) == 2
    assert options[0]['label'] == 'Пациент: ID 1'
    assert options[1]['label'] == 'Пациент: ID 2'


def test_build_scatter_figure_builds_plot_for_complete_data():
    df = pd.DataFrame({
        'ID': [1, 1],
        'Эритроциты': [4.5, 5.0],
        'Дата': ['2020-02-02', '2020-03-03'],
        'Гемоглобин': [13.2, 14.1],
        'Пол': ['F', 'F'],
        'Возраст': [30, 40]
    })

    fig = build_scatter_figure(df)

    assert len(fig.data) == 1
    scatter = fig.data[0]
    assert list(scatter.x) == [4.5, 5.0]
    assert list(scatter.y) == [13.2, 14.1]


def test_build_scatter_figure_handles_missing_columns():
    df = pd.DataFrame({'Эритроциты': [4.5], 'Гемоглобин': [13.2]})
    fig = build_scatter_figure(df)

    assert len(fig.data) == 1
    assert 'Загрузите анализы' in fig.layout.title.text
