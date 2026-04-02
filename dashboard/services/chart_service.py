import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from dashboard.models import DatasetInfo, ChartConfig
from dashboard.services.data_processor import DataProcessorService


# ── Cyberpunk color palette matching the UI theme ──
PALETTE = {
    'cyan':      {'bg': 'rgba(0,240,255,0.65)',  'border': '#00f0ff'},
    'magenta':   {'bg': 'rgba(255,0,170,0.6)',   'border': '#ff00aa'},
    'lime':      {'bg': 'rgba(168,255,0,0.6)',   'border': '#a8ff00'},
    'amber':     {'bg': 'rgba(255,184,0,0.6)',   'border': '#ffb800'},
    'purple':    {'bg': 'rgba(136,77,255,0.6)',  'border': '#884dff'},
    'teal':      {'bg': 'rgba(0,210,190,0.6)',   'border': '#00d2be'},
    'coral':     {'bg': 'rgba(255,107,107,0.6)', 'border': '#ff6b6b'},
    'sky':       {'bg': 'rgba(77,171,247,0.6)',  'border': '#4dabf7'},
    'pink':      {'bg': 'rgba(255,105,180,0.6)', 'border': '#ff69b4'},
    'mint':      {'bg': 'rgba(0,255,170,0.5)',   'border': '#00ffaa'},
}

PALETTE_LIST = list(PALETTE.values())

GRADIENT_FILLS = [
    'rgba(0,240,255,0.08)',
    'rgba(255,0,170,0.08)',
    'rgba(168,255,0,0.08)',
    'rgba(255,184,0,0.08)',
    'rgba(136,77,255,0.08)',
]


def _colors(count: int) -> Dict[str, List[str]]:
    """Return {background:[], border:[]} with cycling palette."""
    bg, bd = [], []
    for i in range(count):
        p = PALETTE_LIST[i % len(PALETTE_LIST)]
        bg.append(p['bg'])
        bd.append(p['border'])
    return {'background': bg, 'border': bd}


def _round_val(v):
    """Smart rounding for display. Converts numpy types to native Python."""
    if v is None:
        return 0
    # Convert numpy types to native Python
    if hasattr(v, 'item'):
        v = v.item()
    if isinstance(v, (np.integer,)):
        v = int(v)
    if isinstance(v, (np.floating,)):
        v = float(v)
    if isinstance(v, float) and np.isnan(v):
        return 0
    if isinstance(v, float):
        if abs(v) >= 1_000_000:
            return round(v / 1_000_000, 1)
        if abs(v) >= 1_000:
            return round(v, 1)
        return round(v, 2)
    if isinstance(v, int):
        return v
    return v


def _fmt_label(v) -> str:
    """Format a value as a chart label. Handles numpy types."""
    if hasattr(v, 'item'):
        v = v.item()
    if isinstance(v, (np.integer,)):
        v = int(v)
    if isinstance(v, (np.floating,)):
        v = float(v)
    if isinstance(v, float):
        if v == int(v):
            return str(int(v))
        return f"{v:.2f}"
    return str(v)


class ChartDataService:
    """Production-quality chart data generation."""

    def __init__(self):
        self.data_processor = DataProcessorService()

    # ── Main dispatcher ─────────────────────────────────────────────
    def generate_chart_data(self, chart_config: ChartConfig) -> Dict[str, Any]:
        dataset_info = chart_config.dashboard.dataset
        df = self.data_processor.get_cached_dataframe(dataset_info)

        if chart_config.filters:
            df = self._apply_filters(df, chart_config.filters)

        generators = {
            'bar': self._bar,
            'line': self._line,
            'pie': self._pie,
            'scatter': self._scatter,
            'histogram': self._histogram,
            'box': self._box,
        }
        gen = generators.get(chart_config.chart_type)
        if not gen:
            raise ValueError(f"Unsupported chart type: {chart_config.chart_type}")
        return gen(df, chart_config)

    # ── Filters ─────────────────────────────────────────────────────
    def _apply_filters(self, df: pd.DataFrame, filters: Dict) -> pd.DataFrame:
        out = df.copy()
        for col, cfg in filters.items():
            if col not in out.columns:
                continue
            ft, v = cfg.get('type', 'equals'), cfg.get('value')
            if ft == 'equals':
                out = out[out[col] == v]
            elif ft == 'not_equals':
                out = out[out[col] != v]
            elif ft == 'greater_than':
                out = out[out[col] > v]
            elif ft == 'less_than':
                out = out[out[col] < v]
            elif ft == 'between':
                out = out[(out[col] >= v[0]) & (out[col] <= v[1])]
            elif ft == 'in':
                out = out[out[col].isin(v)]
            elif ft == 'contains':
                out = out[out[col].astype(str).str.contains(str(v), na=False)]
        return out

    # ── Aggregation helper ──────────────────────────────────────────
    def _agg(self, df, x_col, y_col, agg):
        """Aggregate dataframe by x_col applying agg on y_col."""
        if agg == 'sum':
            return df.groupby(x_col)[y_col].sum()
        elif agg == 'avg':
            return df.groupby(x_col)[y_col].mean()
        elif agg == 'count':
            return df.groupby(x_col)[y_col].count()
        elif agg == 'max':
            return df.groupby(x_col)[y_col].max()
        elif agg == 'min':
            return df.groupby(x_col)[y_col].min()
        return df.groupby(x_col)[y_col].count()

    # ── BAR CHART ───────────────────────────────────────────────────
    def _bar(self, df: pd.DataFrame, cfg: ChartConfig) -> Dict:
        x, y, agg = cfg.x_axis, cfg.y_axis, cfg.aggregation

        if not x:
            raise ValueError("X-axis column is required for bar chart")

        if y and y in df.columns and x != y:
            if agg in ('sum', 'avg', 'max', 'min') and not pd.api.types.is_numeric_dtype(df[y]):
                agg = 'count'
            data = self._agg(df, x, y, agg)
        else:
            data = df[x].value_counts()
            y = 'count'

        # Limit to top 15 and sort descending
        data = data.sort_values(ascending=False).head(15).sort_values(ascending=True)
        labels = [_fmt_label(v) for v in data.index]
        values = [_round_val(v) for v in data.values]
        c = _colors(len(labels))

        ds_label = f'{agg.title()} of {y}' if y != 'count' else 'Count'

        return {
            'type': 'bar',
            'data': {
                'labels': labels,
                'datasets': [{
                    'label': ds_label,
                    'data': values,
                    'backgroundColor': c['background'],
                    'borderColor': c['border'],
                    'borderWidth': 1,
                    'borderRadius': 4,
                    'barPercentage': 0.7,
                }]
            },
            'options': {
                'indexAxis': 'y' if len(labels) > 6 else 'x',
                'responsive': True,
                'maintainAspectRatio': False,
                'plugins': {
                    'legend': {'display': False},
                },
                'scales': {
                    'x' if len(labels) > 6 else 'y': {
                        'beginAtZero': True,
                        'grid': {'color': 'rgba(30,42,66,0.5)'},
                        'ticks': {'color': '#6b7a99', 'font': {'size': 10}}
                    },
                    'y' if len(labels) > 6 else 'x': {
                        'grid': {'display': False},
                        'ticks': {'color': '#6b7a99', 'font': {'size': 10}}
                    }
                }
            }
        }

    # ── LINE CHART ──────────────────────────────────────────────────
    def _line(self, df: pd.DataFrame, cfg: ChartConfig) -> Dict:
        x, y, agg = cfg.x_axis, cfg.y_axis, cfg.aggregation

        if not x or not y:
            raise ValueError("Both X and Y axes required for line chart")

        df_sorted = df.sort_values(x)

        if agg in ('sum', 'avg', 'count', 'max', 'min'):
            data = self._agg(df_sorted, x, y, agg).reset_index()
        else:
            data = df_sorted[[x, y]].dropna()

        # Limit to 50 points for readability
        if len(data) > 50:
            step = max(1, len(data) // 50)
            data = data.iloc[::step]

        labels = [_fmt_label(v) for v in data[x]]
        values = [_round_val(v) for v in data[y]]

        return {
            'type': 'line',
            'data': {
                'labels': labels,
                'datasets': [{
                    'label': f'{agg.title()} of {y}' if agg != 'none' else y,
                    'data': values,
                    'borderColor': '#00f0ff',
                    'backgroundColor': 'rgba(0,240,255,0.06)',
                    'borderWidth': 2,
                    'fill': True,
                    'tension': 0.35,
                    'pointRadius': 2,
                    'pointHoverRadius': 5,
                    'pointBackgroundColor': '#00f0ff',
                    'pointBorderColor': '#00f0ff',
                    'pointHoverBackgroundColor': '#fff',
                    'pointHoverBorderColor': '#00f0ff',
                }]
            },
            'options': {
                'responsive': True,
                'maintainAspectRatio': False,
                'interaction': {'mode': 'index', 'intersect': False},
                'scales': {
                    'x': {
                        'grid': {'color': 'rgba(30,42,66,0.5)'},
                        'ticks': {'color': '#6b7a99', 'font': {'size': 10}, 'maxRotation': 45}
                    },
                    'y': {
                        'beginAtZero': True,
                        'grid': {'color': 'rgba(30,42,66,0.5)'},
                        'ticks': {'color': '#6b7a99', 'font': {'size': 10}}
                    }
                }
            }
        }

    # ── PIE / DONUT CHART ──────────────────────────────────────────
    def _pie(self, df: pd.DataFrame, cfg: ChartConfig) -> Dict:
        x, y, agg = cfg.x_axis, cfg.y_axis, cfg.aggregation

        col = y if y else x
        if not col:
            raise ValueError("At least one axis required for pie chart")

        if x and y and x != y and pd.api.types.is_numeric_dtype(df[y]):
            data = self._agg(df, x, y, agg)
        else:
            data = df[col].value_counts()

        # Top 8 + "Other"
        if len(data) > 8:
            top = data.head(7)
            other_val = data.iloc[7:].sum()
            top = pd.concat([top, pd.Series({'Other': other_val})])
            data = top

        labels = [_fmt_label(v) for v in data.index]
        values = [_round_val(v) for v in data.values]
        c = _colors(len(labels))
        total = sum(values)

        return {
            'type': 'doughnut',
            'data': {
                'labels': labels,
                'datasets': [{
                    'data': values,
                    'backgroundColor': c['background'],
                    'borderColor': c['border'],
                    'borderWidth': 2,
                    'hoverOffset': 8,
                }]
            },
            'options': {
                'responsive': True,
                'maintainAspectRatio': False,
                'cutout': '55%',
                'plugins': {
                    'legend': {
                        'position': 'right',
                        'labels': {
                            'color': '#6b7a99',
                            'font': {'size': 11},
                            'padding': 12,
                            'usePointStyle': True,
                            'pointStyleWidth': 8,
                        }
                    },
                    'tooltip': {
                        'callbacks': {
                            'label': 'function(c) { var t=c.dataset.data.reduce(function(a,b){return a+b},0); return c.label + ": " + c.parsed.toLocaleString() + " (" + Math.round(c.parsed/t*100) + "%)"; }'
                        }
                    }
                }
            }
        }

    # ── SCATTER PLOT ────────────────────────────────────────────────
    def _scatter(self, df: pd.DataFrame, cfg: ChartConfig) -> Dict:
        x, y = cfg.x_axis, cfg.y_axis
        if not x or not y:
            raise ValueError("Both X and Y axes required for scatter plot")

        clean = df[[x, y]].dropna()

        # Check if both are numeric
        if not pd.api.types.is_numeric_dtype(clean[x]):
            # Try to convert
            clean[x] = pd.to_numeric(clean[x], errors='coerce')
            clean = clean.dropna()
        if not pd.api.types.is_numeric_dtype(clean[y]):
            clean[y] = pd.to_numeric(clean[y], errors='coerce')
            clean = clean.dropna()

        if len(clean) == 0:
            raise ValueError(f"No valid numeric data for scatter plot")

        # Sample for performance
        if len(clean) > 500:
            clean = clean.sample(500, random_state=42)

        points = [{'x': float(row[x]), 'y': float(row[y])} for _, row in clean.iterrows()]

        # Calculate correlation for subtitle
        corr = clean[x].corr(clean[y])
        corr_text = f"r = {corr:.3f}" if not np.isnan(corr) else ""

        return {
            'type': 'scatter',
            'data': {
                'datasets': [{
                    'label': f'{y} vs {x}',
                    'data': points,
                    'backgroundColor': 'rgba(0,240,255,0.4)',
                    'borderColor': '#00f0ff',
                    'borderWidth': 1,
                    'pointRadius': 4,
                    'pointHoverRadius': 7,
                    'pointHoverBackgroundColor': '#ff00aa',
                }]
            },
            'options': {
                'responsive': True,
                'maintainAspectRatio': False,
                'plugins': {
                    'subtitle': {
                        'display': bool(corr_text),
                        'text': corr_text,
                        'color': '#6b7a99',
                        'font': {'size': 11, 'style': 'italic'}
                    }
                },
                'scales': {
                    'x': {
                        'title': {'display': True, 'text': x, 'color': '#6b7a99', 'font': {'size': 11}},
                        'grid': {'color': 'rgba(30,42,66,0.5)'},
                        'ticks': {'color': '#6b7a99', 'font': {'size': 10}}
                    },
                    'y': {
                        'title': {'display': True, 'text': y, 'color': '#6b7a99', 'font': {'size': 11}},
                        'grid': {'color': 'rgba(30,42,66,0.5)'},
                        'ticks': {'color': '#6b7a99', 'font': {'size': 10}}
                    }
                }
            }
        }

    # ── HISTOGRAM ───────────────────────────────────────────────────
    def _histogram(self, df: pd.DataFrame, cfg: ChartConfig) -> Dict:
        col = cfg.x_axis or cfg.y_axis
        if not col:
            raise ValueError("Column required for histogram")

        numeric = pd.to_numeric(df[col], errors='coerce').dropna()
        if len(numeric) == 0:
            raise ValueError(f"Column '{col}' has no numeric data")

        # Use Sturges' rule for optimal bin count
        n_bins = int(np.ceil(1 + np.log2(len(numeric))))
        n_bins = max(5, min(n_bins, 30))

        hist, edges = np.histogram(numeric, bins=n_bins)

        labels = []
        for i in range(len(edges) - 1):
            lo, hi = _round_val(edges[i]), _round_val(edges[i + 1])
            labels.append(f"{lo} - {hi}")

        values = [int(v) for v in hist]
        c = _colors(len(values))

        # Stats for subtitle
        mean, std = float(numeric.mean()), float(numeric.std())
        stats_text = f"μ={_round_val(mean)}  σ={_round_val(std)}  n={len(numeric)}"

        return {
            'type': 'bar',
            'data': {
                'labels': labels,
                'datasets': [{
                    'label': 'Frequency',
                    'data': values,
                    'backgroundColor': 'rgba(136,77,255,0.5)',
                    'borderColor': '#884dff',
                    'borderWidth': 1,
                    'borderRadius': 3,
                    'barPercentage': 1.0,
                    'categoryPercentage': 1.0,
                }]
            },
            'options': {
                'responsive': True,
                'maintainAspectRatio': False,
                'plugins': {
                    'legend': {'display': False},
                    'subtitle': {
                        'display': True,
                        'text': stats_text,
                        'color': '#6b7a99',
                        'font': {'size': 11, 'style': 'italic'}
                    }
                },
                'scales': {
                    'x': {
                        'title': {'display': True, 'text': col, 'color': '#6b7a99', 'font': {'size': 11}},
                        'grid': {'display': False},
                        'ticks': {'color': '#6b7a99', 'font': {'size': 9}, 'maxRotation': 45}
                    },
                    'y': {
                        'beginAtZero': True,
                        'title': {'display': True, 'text': 'Frequency', 'color': '#6b7a99', 'font': {'size': 11}},
                        'grid': {'color': 'rgba(30,42,66,0.5)'},
                        'ticks': {'color': '#6b7a99', 'font': {'size': 10}}
                    }
                }
            }
        }

    # ── BOX PLOT (using floating bars) ──────────────────────────────
    def _box(self, df: pd.DataFrame, cfg: ChartConfig) -> Dict:
        col = cfg.x_axis or cfg.y_axis
        if not col:
            raise ValueError("Column required for box plot")

        numeric = pd.to_numeric(df[col], errors='coerce').dropna()
        if len(numeric) == 0:
            raise ValueError(f"Column '{col}' has no numeric data")

        q1 = float(numeric.quantile(0.25))
        med = float(numeric.median())
        q3 = float(numeric.quantile(0.75))
        iqr = q3 - q1
        lo = float(max(numeric.min(), q1 - 1.5 * iqr))
        hi = float(min(numeric.max(), q3 + 1.5 * iqr))
        mean = float(numeric.mean())

        # Use floating bar: base = Q1, height = Q3-Q1
        # Whiskers as separate markers
        return {
            'type': 'bar',
            'data': {
                'labels': [col],
                'datasets': [
                    {
                        'label': 'Whisker Low',
                        'data': [[lo, q1]],
                        'backgroundColor': 'rgba(0,240,255,0.2)',
                        'borderColor': '#00f0ff',
                        'borderWidth': 1,
                        'borderRadius': 2,
                    },
                    {
                        'label': 'IQR (Q1–Q3)',
                        'data': [[q1, q3]],
                        'backgroundColor': 'rgba(0,240,255,0.45)',
                        'borderColor': '#00f0ff',
                        'borderWidth': 2,
                        'borderRadius': 4,
                    },
                    {
                        'label': 'Whisker High',
                        'data': [[q3, hi]],
                        'backgroundColor': 'rgba(0,240,255,0.2)',
                        'borderColor': '#00f0ff',
                        'borderWidth': 1,
                        'borderRadius': 2,
                    },
                ]
            },
            'options': {
                'responsive': True,
                'maintainAspectRatio': False,
                'indexAxis': 'y',
                'plugins': {
                    'legend': {
                        'position': 'top',
                        'labels': {'color': '#6b7a99', 'font': {'size': 10}, 'usePointStyle': True}
                    },
                    'subtitle': {
                        'display': True,
                        'text': f'Median={_round_val(med)}  Mean={_round_val(mean)}  IQR={_round_val(iqr)}',
                        'color': '#6b7a99',
                        'font': {'size': 11, 'style': 'italic'}
                    },
                    'tooltip': {
                        'callbacks': {
                            'label': 'function(c) { var v=c.raw; return c.dataset.label + ": " + v[0].toLocaleString() + " – " + v[1].toLocaleString(); }'
                        }
                    }
                },
                'scales': {
                    'x': {
                        'grid': {'color': 'rgba(30,42,66,0.5)'},
                        'ticks': {'color': '#6b7a99', 'font': {'size': 10}}
                    },
                    'y': {
                        'grid': {'display': False},
                        'ticks': {'color': '#6b7a99', 'font': {'size': 11}}
                    }
                }
            }
        }

    # ── Dataset summary ─────────────────────────────────────────────
    def get_dataset_summary(self, dataset_info: DatasetInfo) -> Dict:
        df = self.data_processor.get_cached_dataframe(dataset_info)

        summary = {
            'total_rows': len(df),
            'total_columns': len(df.columns),
            'numeric_columns': dataset_info.numeric_columns,
            'categorical_columns': dataset_info.categorical_columns,
            'date_columns': dataset_info.date_columns,
            'missing_data': {},
        }

        for col in df.columns:
            mc = int(df[col].isnull().sum())
            mp = round((mc / len(df)) * 100, 2) if len(df) > 0 else 0
            summary['missing_data'][col] = {'count': mc, 'percentage': mp}

        return summary

    # ── SMART SUGGESTIONS ───────────────────────────────────────────
    def get_suggested_charts(self, dataset_info: DatasetInfo) -> List[Dict]:
        """Intelligent chart suggestions based on data characteristics."""
        suggestions = []
        nums = dataset_info.numeric_columns
        cats = dataset_info.categorical_columns
        dates = dataset_info.date_columns

        try:
            df = self.data_processor.get_cached_dataframe(dataset_info)
        except Exception:
            df = None

        # ── CATEGORICAL → Bar chart (count distribution) ──
        for cat in cats[:3]:
            cardinality = 0
            if df is not None:
                cardinality = df[cat].nunique()
            if cardinality <= 2:
                chart_type = 'pie'
            elif cardinality <= 15:
                chart_type = 'bar'
            else:
                chart_type = 'bar'  # will be truncated to top 15

            suggestions.append({
                'type': chart_type,
                'title': f'{cat} Distribution',
                'x_axis': cat,
                'y_axis': '',
                'aggregation': 'count',
            })

        # ── NUMERIC → Histogram ──
        for num in nums[:3]:
            suggestions.append({
                'type': 'histogram',
                'title': f'{num} Distribution',
                'x_axis': num,
                'y_axis': '',
                'aggregation': 'count',
            })

        # ── CATEGORICAL × NUMERIC → Grouped bar ──
        for cat in cats[:2]:
            for num in nums[:2]:
                suggestions.append({
                    'type': 'bar',
                    'title': f'Avg {num} by {cat}',
                    'x_axis': cat,
                    'y_axis': num,
                    'aggregation': 'avg',
                })

        # ── DATE × NUMERIC → Line chart ──
        if dates and nums:
            for d in dates[:1]:
                for num in nums[:2]:
                    suggestions.append({
                        'type': 'line',
                        'title': f'{num} Over Time',
                        'x_axis': d,
                        'y_axis': num,
                        'aggregation': 'sum',
                    })

        # ── NUMERIC × NUMERIC → Scatter (pick best correlated pair) ──
        if len(nums) >= 2 and df is not None:
            best_pair = None
            best_corr = 0
            for i, n1 in enumerate(nums):
                for n2 in nums[i + 1:]:
                    try:
                        c = abs(df[n1].corr(df[n2]))
                        if not np.isnan(c) and c > best_corr:
                            best_corr = c
                            best_pair = (n1, n2)
                    except Exception:
                        pass

            if best_pair:
                suggestions.append({
                    'type': 'scatter',
                    'title': f'{best_pair[1]} vs {best_pair[0]}',
                    'x_axis': best_pair[0],
                    'y_axis': best_pair[1],
                    'aggregation': 'none',
                })
            else:
                # Fallback: just first two numeric columns
                suggestions.append({
                    'type': 'scatter',
                    'title': f'{nums[1]} vs {nums[0]}',
                    'x_axis': nums[0],
                    'y_axis': nums[1],
                    'aggregation': 'none',
                })

        # ── BOX PLOT for numeric ──
        for num in nums[:2]:
            suggestions.append({
                'type': 'box',
                'title': f'{num} Box Plot',
                'x_axis': num,
                'y_axis': '',
                'aggregation': 'none',
            })

        # ── CATEGORICAL × NUMERIC → Pie (if low cardinality) ──
        if cats and nums:
            for cat in cats[:1]:
                for num in nums[:1]:
                    suggestions.append({
                        'type': 'pie',
                        'title': f'{num} by {cat}',
                        'x_axis': cat,
                        'y_axis': num,
                        'aggregation': 'sum',
                    })

        return suggestions[:12]
