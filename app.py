import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import os
import csv
import webbrowser
import sys
import platform

import linkfinder
import linkfilter
import scrapper

class StdoutRedirector:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, s):
        self.text_widget.insert(tk.END, s)
        self.text_widget.see(tk.END)

    def flush(self):
        pass

class ScrappyApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Scrappy App")
        self.geometry("750x550")
        self.configure(bg="#e3f6f5")  # Soft teal background

        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('TLabel', background="#e3f6f5", font=('Segoe UI', 11))
        style.configure('TButton', font=('Segoe UI', 11), background="#43aa8b", foreground="#fff")
        style.configure('TEntry', font=('Segoe UI', 11))
        style.configure('TSpinbox', font=('Segoe UI', 11))
        style.configure("green.Horizontal.TProgressbar", troughcolor="#b8f2e6", bordercolor="#b8f2e6",
                        background="#43aa8b", lightcolor="#43aa8b", darkcolor="#43aa8b")

        self.title_label = ttk.Label(self, text="Scrappy App", font=('Segoe UI', 18, 'bold'), background="#e3f6f5", foreground="#006d77")
        self.title_label.pack(pady=(15, 5))

        input_frame = tk.Frame(self, bg="#b8f2e6", bd=2, relief="groove")
        input_frame.pack(pady=10, padx=10, fill=tk.X)

        self.query_label = ttk.Label(input_frame, text="Search Query:")
        self.query_label.grid(row=0, column=0, sticky='e', padx=5, pady=5)
        self.query_entry = ttk.Entry(input_frame, width=50, foreground='grey')
        self.query_entry.insert(0, "business type + city + state")
        self.query_entry.bind("<FocusIn>", self.clear_placeholder)
        self.query_entry.bind("<FocusOut>", self.add_placeholder)
        self.query_entry.grid(row=0, column=1, padx=5, pady=5)

        self.pages_label = ttk.Label(input_frame, text="How many pages to search?")
        self.pages_label.grid(row=1, column=0, sticky='e', padx=5, pady=5)
        self.pages_spinbox = ttk.Spinbox(input_frame, from_=1, to=20, width=5)
        self.pages_spinbox.grid(row=1, column=1, sticky='w', padx=5, pady=5)

        self.start_button = ttk.Button(self, text="Start Finding Links", command=self.find_links)
        self.start_button.pack(pady=(0, 10))

        # Progress bar (green, animated)
        self.progress = ttk.Progressbar(self, orient='horizontal', length=500, mode='indeterminate', style="green.Horizontal.TProgressbar")
        self.progress.pack(pady=(0, 10))

        self.log_text = scrolledtext.ScrolledText(self, height=18, width=90, state='normal', font=('Consolas', 10), bg="#f0fff3")
        self.log_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        sys.stdout = StdoutRedirector(self.log_text)

        self.csv_file = None

    def clear_placeholder(self, event):
        if self.query_entry.get() == "business type + city + state":
            self.query_entry.delete(0, tk.END)
            self.query_entry.config(foreground='black')

    def add_placeholder(self, event):
        if not self.query_entry.get():
            self.query_entry.insert(0, "business type + city + state")
            self.query_entry.config(foreground='grey')

    def set_progress(self, value=None, text="", animate=False):
        if animate:
            self.progress.config(mode='indeterminate')
            self.progress.start(10)
        else:
            self.progress.stop()
            self.progress.config(mode='determinate')
            if value is not None:
                self.progress['value'] = value
        self.update_idletasks()
        if text:
            print(f"[Progress] {text}")

    def find_links(self):
        query = self.query_entry.get()
        if query == "business type + city + state" or not query.strip():
            messagebox.showerror("Error", "Please enter a valid search query.")
            return
        try:
            pages = int(self.pages_spinbox.get())
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number of pages.")
            return

        if not messagebox.askokcancel("Start", f"Start finding links for '{query}' on {pages} pages?"):
            return

        self.set_progress(text="Starting Google search...", animate=True)
        self.after(100, lambda: self._find_links_task(query, pages))

    def _find_links_task(self, query, pages):
        print(f"\n🔍 Searching for: {query} ({pages} pages)")
        results = linkfinder.google_search_scrape_local(query, num_pages=pages)
        filename = "scraped_links.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=4)
        print(f"Links saved to {filename}\n")
        self.set_progress(30, "Links found.", animate=False)
        self.ask_filter(filename)

    def ask_filter(self, input_json):
        if messagebox.askyesno("Filter", "Do you want to filter the list?"):
            self.set_progress(text="Filtering links...", animate=True)
            self.after(100, lambda: self._filter_task(input_json))
        else:
            self.ask_scrape(input_json)

    def _filter_task(self, input_json):
        with open(input_json, "r", encoding="utf-8") as f:
            scraped = json.load(f)
        out = linkfilter.select_business_sites(scraped, want=10, max_domains_to_check=80)
        with open("domain_scores_debug.json", "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)
        filtered_file = "selected_sites.json"
        with open(filtered_file, "w", encoding="utf-8") as f:
            json.dump([site["kept_url"] for site in out["selected"] if site.get("kept_url")], f, indent=2)
        print(f"Filtered list saved to {filtered_file}")
        print(f"Original list: {input_json}")
        print("The original list contains all found links.")
        print("The filtered list contains only business sites.\n")
        self.set_progress(60, "Filtering complete.", animate=False)
        self.ask_scrape(filtered_file)

    def ask_scrape(self, input_json):
        if messagebox.askyesno("Scrape", "Do you want to run the scraper on the list?"):
            self.set_progress(text="Scraping sites...", animate=True)
            self.after(100, lambda: self._scrape_task(input_json))
        else:
            self.set_progress(100, "Done.", animate=False)

    def _scrape_task(self, input_json):
        output_json = "scraped_data.json"
        scrapper.scrape_sites_from_json(input_json, output_json)
        print(f"Scraped data saved to {output_json}\n")
        self.set_progress(85, "Scraping complete.", animate=False)
        self.ask_convert(output_json)

    def ask_convert(self, json_file):
        if messagebox.askyesno("Convert", "Convert the JSON to CSV?"):
            self.set_progress(text="Converting to CSV...", animate=True)
            self.after(100, lambda: self._convert_task(json_file))
        else:
            self.set_progress(100, "Done.", animate=False)

    def _convert_task(self, json_file):
        csv_file = json_file.replace(".json", ".csv")
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data = list(data.values())
        if data and isinstance(data[0], dict):
            keys = data[0].keys()
            with open(csv_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(data)
            print(f"CSV saved to {csv_file}\n")
            self.csv_file = csv_file
            self.set_progress(100, "All done!", animate=False)
            webbrowser.open("https://sheets.new")
            messagebox.showinfo("Google Sheets", "A new Google Sheet has been opened in your browser. You can upload the CSV there.")
            self.ask_open_folder()
        else:
            messagebox.showerror("Error", "Data format not suitable for CSV conversion.")
            self.set_progress(100, "Done.", animate=False)

    def ask_open_folder(self):
        if self.csv_file and messagebox.askyesno("Open Folder", "Do you want to open the folder containing the CSV file?"):
            folder = os.path.abspath(os.path.dirname(self.csv_file))
            if platform.system() == "Windows":
                os.startfile(folder)
            elif platform.system() == "Darwin":
                os.system(f'open "{folder}"')
            else:
                os.system(f'xdg-open "{folder}"')
            print(f"Opened folder: {folder}\n")

def main():
    app = ScrappyApp()
    app.mainloop()

if __name__ == "__main__":
    main()