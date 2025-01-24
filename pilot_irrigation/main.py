import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt
from gui.tabs.network_tab import NetworkTab
from gui.tabs.strahler_tab import StrahlerTab

class IrrigationSystem(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Qushtepa Pilot Irrigation System")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Create tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Initialize tabs
        self.init_tabs()
        
    def init_tabs(self):
        # Tab 1: Network Analysis
        self.network_tab = NetworkTab()
        self.tabs.addTab(self.network_tab, "Network Analysis")
        
        # Tab 2: Strahler Analysis
        self.strahler_tab = StrahlerTab()
        # Connect network_processed signal from network_tab to strahler_tab
        self.network_tab.network_processed.connect(self.on_network_processed)
        self.network_tab.proceed_to_strahler.connect(self.switch_to_strahler)
        self.tabs.addTab(self.strahler_tab, "Strahler Analysis")
        
        # Other tabs as placeholders
        placeholder_tabs = [
            "Facility Attributes",
            "Network Limits",
            "Field Requirements",
            "Irrigation Plan",
            "Measurements",
            "Reports"
        ]
        
        for tab_name in placeholder_tabs:
            self.tabs.addTab(QWidget(), tab_name)
            
    def on_network_processed(self, network):
        """Handle processed network from NetworkAnalysisTab"""
        # Pass the processed network to StrahlerTab
        if hasattr(self, 'strahler_tab'):
            self.strahler_tab.network = network
            self.strahler_tab.start_analysis()
            
    def switch_to_strahler(self):
        """Switch to Strahler Analysis tab"""
        strahler_index = self.tabs.indexOf(self.strahler_tab)
        self.tabs.setCurrentIndex(strahler_index)

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Set Fusion style for better cross-platform appearance
    window = IrrigationSystem()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()