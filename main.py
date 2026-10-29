import io
import os
from functools import wraps
from PIL import Image, ImageEnhance
from flask import Flask, redirect, jsonify, url_for, request, abort, send_file, render_template
import database
from domain import Color, Source, SourceKind, SourceFrame, SourceService
import render
import ingester
import environment

database.update_schema()

app = Flask(__name__)

def require_appkey(request_func):
    @wraps(request_func)

    def decoreated_func(*args, **kwargs):
        
        key = request.args.get('key') 

        print(f"checking auth, key = {key}")

        if key and key == environment.REMOTE_APIKEY and len(environment.REMOTE_APIKEY) > 0:
            return request_func(*args, **kwargs)
        else:
            abort(401)

    return decoreated_func

@app.route('/api/source/<int:source_id>/render', methods=['GET'])
def api_get_source_render(source_id):
    
    height = request.args.get('height', default=900, type=int)
    width = request.args.get('width', default=1000, type=int)
    strip_width = request.args.get('strip_width', default=5, type=int)
    max_strips = request.args.get('max_strips', default=1000, type=int)
    kind = request.args.get('kind', default=0, type=int) # gotta add an enum for the render kind... someone do that later
    radius = request.args.get('radius', default=400, type=int)
    radius_inner = request.args.get('radius_inner', default=20, type=int)
    
    fi_enhancement_color = request.args.get('fi_enhancement_color', default=1.0, type=float)
    fi_enhancement_contrast = request.args.get('fi_enhancement_contrast', default=1.0, type=float)
    fi_enhancement_brightness = request.args.get('fi_enhancement_brightness', default=1.0, type=float)
    fi_enhancement_sharpness = request.args.get('fi_enhancement_sharpness', default=1.0, type=float)

    f_ = request.args.get('f_', default=0, type=int)
    f_bg_r = request.args.get("f_bg_r", default=250, type=int)
    f_bg_g = request.args.get("f_bg_g", default=250, type=int)
    f_bg_b = request.args.get("f_bg_b", default=250, type=int)
    f_fg_r = request.args.get("f_fg_r", default=0, type=int)
    f_fg_g = request.args.get("f_fg_g", default=0, type=int)
    f_fg_b = request.args.get("f_fg_b", default=0, type=int)
    f_h_h = request.args.get("f_h_h", default=20, type=int)

    #f_t_l = request.args.get("f_t_l", default="frame title", type=str)

    #print(f"request processing... f_: {f_}")

    conn = database.create_connection()

    source = SourceService.get_source_by_id(conn, source_id)
    
    frames = SourceService.get_source_frames(conn, source_id)

    data = []

    for f in frames:
        data.append(f.color)

    if kind == 0:
        img : Image = render.render_force_max_lines_force_size(data, height, strip_width, max_strips, width)
    elif kind == 1:
        img : Image = render.render_circle(data, radius, radius_inner, max_strips, width, height)
    elif kind == 2:
        img : Image = render.render_circle_2(data, width, height, max_strips)

    if fi_enhancement_color != 1.0:
        img = ImageEnhance.Color(img).enhance(fi_enhancement_color)
    if fi_enhancement_contrast != 1.0:
        img = ImageEnhance.Contrast(img).enhance(fi_enhancement_contrast)
    if fi_enhancement_brightness != 1.0:
        img = ImageEnhance.Brightness(img).enhance(fi_enhancement_brightness)
    if fi_enhancement_sharpness != 1.0:
        img = ImageEnhance.Sharpness(img).enhance(fi_enhancement_sharpness)

    if f_ == 1:
        img : Image = render.render_frame(f"{source.metadata_name} ({source.metadata_year})", "", img, Color(f_bg_r, f_bg_g, f_bg_b), Color(f_fg_r, f_fg_g, f_fg_b), f_h_h, width, height)
    
    img_io = io.BytesIO()
    
    img.save(img_io, 'PNG')
    
    img_io.seek(0)

    return send_file(img_io, mimetype='image/png')

@app.route('/api/source/list', methods=['GET'])
def api_get_source_list():
    conn = database.create_connection()
    sources = SourceService.get_sources(conn)
    return jsonify([s.__dict__ for s in sources])

@app.route('/api/source', methods=['POST'])
@require_appkey
def api_set_source():
    content = request.get_json()

    s : Source = Source()

    s.sha512 = content['sha512']
    s.imdb_id = content['imdb_id']
    s.kind = content['kind']
    s.metadata_name = content['metadata_name']
    s.metadata_year = content['metadata_year']

    conn = database.create_connection()

    s.id = SourceService.create_source(conn, s, False)

    frames = []

    for i, f in enumerate(content['frames']):
        sf : SourceFrame = SourceFrame()

        sf.frame_index = i
        sf.color_r = f["color_r"]
        sf.color_g = f["color_g"]
        sf.color_b = f["color_b"]

        sf.id = SourceService.create_source_frame(conn, s.id, sf, False)

        frames.append(sf)

    conn.commit()    

    return jsonify({ "source_id" : s.id, "frame_count" : len(frames)})

@app.route('/api/source/lookup', methods=['GET'])
def asi_source_lookup():
    conn = database.create_connection()

    imdb_id = request.args.get('imdb_id', default="", type=str)
    sha512 = request.args.get('sha512', default="", type=str)

    source_id = SourceService.lookup_source(conn, sha512, imdb_id)

    if source_id == 0:
        abort(404)

    return jsonify({"source_id" : source_id})

@app.route('/')
def get_landing():
    return redirect(url_for('get_source_list'))

@app.route('/source/list', methods=['GET'])
def get_source_list():
    conn = database.create_connection()
    sources = SourceService.get_sources(conn)

    return render_template('source_list.html', sources=sources)

@app.route('/source/<int:source_id>/render', methods=['GET'])
def get_source_render(source_id):
    height = request.args.get('height', default=900, type=int)
    width = request.args.get('width', default=1000, type=int)
    strip_width = request.args.get('strip_width', default=5, type=int)
    max_strips = request.args.get('max_strips', default=1000, type=int)
    kind = request.args.get('kind', default=0, type=int) # gotta add an enum for the render kind... someone do that latter
    radius = request.args.get('radius', default=400, type=int)
    radius_inner = request.args.get('radius_inner', default=20, type=int)
    fi_enhancement_color = request.args.get('fi_enhancement_color', default=1.0, type=float)
    fi_enhancement_contrast = request.args.get('fi_enhancement_contrast', default=1.0, type=float)
    fi_enhancement_brightness = request.args.get('fi_enhancement_brightness', default=1.0, type=float)
    fi_enhancement_sharpness = request.args.get('fi_enhancement_sharpness', default=1.0, type=float)
    f_ = request.args.get('f_', default=0, type=int)

    conn = database.create_connection()
    source = SourceService.get_source_by_id(conn, source_id)
    frames = SourceService.get_source_frames(conn, source_id)

    return render_template('source_render.html', 
                           source=source, 
                           frames=frames, 
                           height=height, 
                           width=width, 
                           strip_width=strip_width, 
                           max_strips=max_strips, 
                           kind=kind, 
                           radius=radius, 
                           radius_inner=radius_inner,
                           f_=f_,
                           fi_enhancement_color=fi_enhancement_color,
                           fi_enhancement_contrast=fi_enhancement_contrast,
                           fi_enhancement_brightness=fi_enhancement_brightness,
                           fi_enhancement_sharpness=fi_enhancement_sharpness)

@app.route('/contributors', methods=['GET'])
def get_contributors():
    return render_template('contributors.html')

@app.route('/static/<path:filename>')
def static_file(filename):
    return send_file(os.path.join('static', 'css', filename))

if __name__ == "__main__":
    app.run()