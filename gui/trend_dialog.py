import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from datetime import datetime

from PyQt5.QtWidgets import QDialog, QVBoxLayout
from PyQt5.QtCore import Qt


class TrendGraphDialog(QDialog):
    def __init__(self, data, legend_colors, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle("Historical Analysis Trends")
        self.resize(1000, 800)
        self.data = data
        self.legend_colors = legend_colors
        
        # Layout
        layout = QVBoxLayout(self)
        
        # Matplotlib Figure
        self.figure = Figure(figsize=(15, 12))
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        
        self.plot_graphs()
        
    def plot_graphs(self):
        self.figure.clear()
        
        # Create subplots manually
        axes = self.figure.subplots(4, 2)
        self.figure.suptitle("Historical Trends", fontsize=16)
        axes = axes.flatten()
        
        indices = ['NDVI', 'GNDVI', 'NDWI', 'NDRE', 'EVI', 'SAVI', 'RENDVI']
        
        for i, idx_name in enumerate(indices):
            ax = axes[i]
            for cls_name, cls_data in self.data.items():
                c = self.legend_colors.get(cls_name, 'black')
                
                dates = cls_data['dates']
                vals = cls_data[idx_name]
                
                # Format dates to remove year (YYYY-MM-DD -> DD.MM)
                formatted_dates = []
                for d in dates:
                    try:
                        dt = datetime.strptime(d, "%Y-%m-%d")
                        formatted_dates.append(dt.strftime("%d.%m"))
                    except:
                        formatted_dates.append(d)
                
                ax.plot(formatted_dates, vals, marker='o', label=cls_name, color=c)
            
            ax.set_title(idx_name)
            ax.grid(True, linestyle='--', alpha=0.6)
            
            # Rotate labels
            ax.tick_params(axis='x', rotation=30, labelsize=8)
            
        # Hide 8th subplot axis lines but use it for legend
        axes[7].axis('off')
        
        # Add legend to the empty 8th subplot
        handles, labels = axes[0].get_legend_handles_labels()
        if handles:
            axes[7].legend(handles, labels, loc='center', fontsize='10', title="Product Legend", frameon=True)
        
        self.figure.tight_layout()
        self.canvas.draw()
