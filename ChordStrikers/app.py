from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
import os
from pathlib import Path
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///songs.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'dev'  # for flash messages (optional)

db = SQLAlchemy(app)

def normalise_spacing(text: str) -> str:
    lines = text.splitlines()
    cleaned = []
    blank = False
    for line in lines:
        if line.strip() == "":
            if not blank:
                cleaned.append("")  # keep a single blank
            blank = True
        else:
            cleaned.append(line.rstrip())
            blank = False
    return "\n".join(cleaned)

class Song(db.Model):
    __tablename__ = 'songs'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    artist = db.Column(db.String(150), nullable=False, index=True)
    song_key = db.Column(db.String(12), nullable=True, index=True)
    data_path = db.Column(db.String(255), nullable=True)  # relative to /static

    def __repr__(self):
        return f"<Song {self.id} {self.title} - {self.artist} ({self.song_key})>"

# ✅ Create tables only if missing
with app.app_context():
    inspector = db.inspect(db.engine)
    if not inspector.has_table("songs"):
        db.create_all()
        print("Tables created.")
    else:
        print("Tables already exist — skipping create_all().")

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/creator", methods=["GET"])
def creator():
    return render_template("creator.html")

@app.route("/create", methods=["POST"])
def create():
    title = (request.form.get("title") or "").strip()
    artist = (request.form.get("artist") or "").strip()
    song_key = (request.form.get("song_key") or request.form.get("key") or "").strip()

    if not title or not artist:
        flash("Title and Artist are required.")
        return redirect(url_for("creator"))

    data_path = None
    save_dir = os.path.join(app.static_folder, "data")
    os.makedirs(save_dir, exist_ok=True)

    # 2️⃣ Text content (if no file uploaded)
    if request.form.get("sheet_content"):
        content = normalise_spacing(request.form.get("sheet_content"))
        base_name = f"{title.replace(' ', '_')}.txt"
        safe_name = secure_filename(base_name)
        file_path = os.path.join(save_dir, safe_name)
        Path(file_path).write_text(content, encoding="utf-8")
        data_path = f"data/{safe_name}"

    # 3️⃣ Save DB entry
    new_song = Song(title=title, artist=artist, song_key=song_key, data_path=data_path)
    db.session.add(new_song)
    db.session.commit()

    flash(f"Song '{title}' by {artist} created successfully!", "success")
    return redirect(url_for("view_sheet", sheet_id=new_song.id))

@app.route("/edit/<int:sheet_id>", methods=["GET", "POST"])
def edit_song(sheet_id):
    song = db.session.get(Song, sheet_id)
    if not song:
        abort(404)

    save_dir = os.path.join(app.static_folder, "data")
    os.makedirs(save_dir, exist_ok=True)

    if request.method == "POST":
        # Always update text attributes directly from form
        song.title = (request.form.get("title") or "").strip()
        song.artist = (request.form.get("artist") or "").strip()
        song.song_key = (request.form.get("song_key") or request.form.get("key") or "").strip()

        # Optional: update relative path if user changes it
        new_data_path = (request.form.get("data_path") or "").strip()
        if new_data_path:
            if not new_data_path.startswith("data/"):
                new_data_path = f"data/{new_data_path}"
            song.data_path = new_data_path

        # Handle direct text edit
        elif request.form.get("sheet_content") is not None:
            sheet_content = normalise_spacing(request.form["sheet_content"])
            if song.data_path:
                file_path = os.path.join(app.static_folder, song.data_path)
            else:
                base_name = f"{song.title.replace(' ', '_')}.txt" or "untitled.txt"
                safe_name = secure_filename(base_name)
                file_path = os.path.join(save_dir, safe_name)
                song.data_path = f"data/{safe_name}"

            Path(file_path).write_text(sheet_content, encoding="utf-8")

        # ✅ Commit after all possible changes
        db.session.commit()

        flash("Chord sheet updated!", "success")
        return redirect(url_for("view_sheet", sheet_id=song.id))

    # GET — prefill sheet content
    sheet_content = ""
    if song.data_path:
        file_path = os.path.join(app.static_folder, song.data_path)
        try:
            sheet_content = Path(file_path).read_text(encoding="utf-8")
        except FileNotFoundError:
            pass

    song.content = sheet_content
    return render_template("edit_sheet.html", song=song)

@app.route("/explore")
def explore():
    query = (request.args.get("query") or "").strip()
    selected_key = (request.args.get("key") or "").strip()

    q = Song.query
    if query:
        like = f"%{query}%"
        q = q.filter(or_(Song.title.ilike(like), Song.artist.ilike(like)))
    if selected_key:
        q = q.filter(Song.song_key.ilike(selected_key))

    chord_sheets = q.order_by(Song.title.asc()).all()
    return render_template("explore.html", chord_sheets=chord_sheets, query=query, selected_key=selected_key)

@app.route("/sheet/<int:sheet_id>")
def view_sheet(sheet_id):
    song = Song.query.get_or_404(sheet_id)

    sheet_content = None
    if song.data_path:
        path = os.path.join(app.static_folder, song.data_path)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                sheet_content = f.read()

    return render_template("view_sheet.html", song=song, sheet_content=sheet_content)

if __name__ == "__main__":
    app.run(debug=True)