# src/services/report_service.py
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from src.db.db_manager import DatabaseManager


class ReportService:
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.font_name = 'Helvetica'  # Запасний шрифт
        self.setup_fonts()

    def setup_fonts(self):
        """Підключення кириличного шрифту."""
        font_path = os.path.join(os.path.dirname(__file__), '../../assets/fonts/DejaVuSans.ttf')
        try:
            pdfmetrics.registerFont(TTFont('CyrillicFont', font_path))
            self.font_name = 'CyrillicFont'
        except Exception as e:
            print(f"Попередження: Шрифт не знайдено за шляхом {font_path}. Кирилиця може відображатись некоректно.")

    def _generate_pdf(self, filename: str, title: str, headers: list, data: list) -> str:
        # Використовуємо абсолютний шлях до кореня
        from reportlab.lib.styles import ParagraphStyle
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
        reports_dir = os.path.join(base_dir, "docs", "reports")
        os.makedirs(reports_dir, exist_ok=True)
        filepath = os.path.join(reports_dir, filename)

        doc = SimpleDocTemplate(filepath, pagesize=A4)
        styles = getSampleStyleSheet()

        # Безпечне створення власного стилю
        title_style = ParagraphStyle('CustomH1', parent=styles['Heading1'], fontName=self.font_name)

        elements = []
        elements.append(Paragraph(title, title_style))
        elements.append(Spacer(1, 12))

        # Компонування таблиці
        table_data = [headers] + data
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), self.font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        elements.append(table)
        doc.build(elements)
        return filepath

    def generate_overdue_report(self) -> tuple[bool, str]:
        """Звіт про заборгованості."""
        query = """
            SELECT r.last_name || ' ' || r.first_name as reader_name, r.phone, b.title, 
                   CAST(julianday('now') - julianday(l.due_date) AS INTEGER) as days
            FROM LOANS l
            JOIN READERS r ON l.reader_id = r.id
            JOIN COPIES c ON l.copy_id = c.id
            JOIN BOOKS b ON c.book_id = b.id
            WHERE l.return_date IS NULL AND l.due_date < DATE('now')
            ORDER BY days DESC
        """
        rows = self.db.fetch_all(query)
        # Звертаємось за іменами колонок замість індексів
        data = [[row['reader_name'], row['phone'], row['title'], str(row['days'])] for row in rows]
        headers = ["Читач", "Телефон", "Книга", "Днів прострочення"]

        filename = f"overdue_report_{datetime.now().strftime('%Y-%m-%d')}.pdf"
        filepath = self._generate_pdf(filename, "Звіт: Прострочені видачі", headers, data)
        return True, f"Звіт згенеровано: {filepath}"

    def generate_popular_books_report(self) -> tuple[bool, str]:
        """Звіт про популярні книги."""
        query = """
            SELECT b.title, a.last_name, COUNT(l.id) as loans_count
            FROM LOANS l
            JOIN COPIES c ON l.copy_id = c.id
            JOIN BOOKS b ON c.book_id = b.id
            LEFT JOIN AUTHORS a ON b.author_id = a.id
            GROUP BY b.id
            ORDER BY loans_count DESC LIMIT 10
        """
        rows = self.db.fetch_all(query)
        # Звертаємось за іменами колонок замість індексів
        data = [[row['title'], row['last_name'] or "Невідомо", str(row['loans_count'])] for row in rows]
        headers = ["Назва книги", "Автор", "Кількість видач"]

        filename = f"popular_books_{datetime.now().strftime('%Y-%m-%d')}.pdf"
        filepath = self._generate_pdf(filename, "Звіт: Топ-10 популярних книг", headers, data)
        return True, f"Звіт згенеровано: {filepath}"

    def generate_movement_report(self, start_date: str, end_date: str) -> tuple[bool, str]:
        """Звіт про рух фонду (видачі та повернення) за обраний період."""
        from datetime import datetime
        query = """
            SELECT b.title, c.inventory_number, l.issue_date, l.return_date, 
                   r.last_name || ' ' || r.first_name as reader_name
            FROM LOANS l
            JOIN COPIES c ON l.copy_id = c.id
            JOIN BOOKS b ON c.book_id = b.id
            JOIN READERS r ON l.reader_id = r.id
            WHERE l.issue_date BETWEEN ? AND ? 
               OR l.return_date BETWEEN ? AND ?
            ORDER BY l.issue_date DESC
        """
        rows = self.db.fetch_all(query, (start_date, end_date, start_date, end_date))

        data = [[row['title'], row['inventory_number'], str(row['issue_date']),
                 str(row['return_date'] or "Не повернуто"), row['reader_name']] for row in rows]
        headers = ["Книга", "Інв. №", "Дата видачі", "Дата повернення", "Читач"]

        filename = f"movement_report_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.pdf"
        filepath = self._generate_pdf(filename, f"Рух фонду ({start_date} до {end_date})", headers, data)
        return True, f"Звіт згенеровано: {filepath}"