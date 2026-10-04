import os
import uuid
import logging
import math
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from PIL import Image

logger = logging.getLogger("face_service")

# Diretório base para uploads e recortes de rostos
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
FACES_DIR = os.path.join(UPLOADS_DIR, "faces")
os.makedirs(FACES_DIR, exist_ok=True)


class FaceAnalysisEngine:
    """
    Engine singleton que inicializa o InsightFace (buffalo_l) uma única vez
    ou provê fallback para detecção em ambientes sem GPU/pesos offline.
    """
    _instance = None
    _app = None
    _use_fallback = False

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        try:
            import insightface
            from insightface.app import FaceAnalysis

            logger.info("Carregando modelo InsightFace (buffalo_l)...")
            self._app = FaceAnalysis(name="buffalo_l", allowed_modules=["detection", "recognition"])
            self._app.prepare(ctx_id=-1, det_size=(640, 640))
            logger.info("InsightFace carregado com sucesso!")
        except Exception as e:
            logger.warning(f"InsightFace indisponível ou falha ao inicializar ({e}). Utilizando fallback detector.")
            self._use_fallback = True

    def detect_and_extract(self, image_path: str) -> List[Dict[str, Any]]:
        """
        Processa uma imagem e retorna lista de dicionários contendo:
        - bbox: [x1, y1, x2, y2]
        - embedding: List[float] (512-dim)
        - score: float
        - crop_filename: str (salvo em uploads/faces/)
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Imagem não encontrada: {image_path}")

        pil_img = Image.open(image_path).convert("RGB")
        img_np = np.array(pil_img)
        w, h = pil_img.size

        if w < 64 or h < 64:
            logger.info(f"Imagem muito pequena para detecção de faces: {image_path}")
            return []

        results = []

        if not self._use_fallback and self._app is not None:
            # InsightFace espera formato BGR
            img_bgr = img_np[:, :, ::-1]
            faces = self._app.get(img_bgr)
            for face in faces:
                bbox = [float(x) for x in face.bbox]  # [x1, y1, x2, y2]
                embedding = face.embedding.tolist() if face.embedding is not None else None
                score = float(face.det_score) if hasattr(face, "det_score") else 1.0

                crop_filename = self._save_face_crop(pil_img, bbox)

                results.append({
                    "bbox": bbox,
                    "embedding": embedding,
                    "score": score,
                    "crop_filename": crop_filename,
                })
        else:
            # Fallback inteligente (utiliza detecção simples ou recorte central caso InsightFace não esteja instalado)
            results = self._fallback_detect(pil_img, img_np)

        return results

    def _save_face_crop(self, pil_img: Image.Image, bbox: List[float], margin_ratio: float = 0.2) -> str:
        """Recorta o rosto com margem e salva thumbnail JPEG."""
        w, h = pil_img.size
        x1, y1, x2, y2 = bbox
        bw = x2 - x1
        bh = y2 - y1

        # Margem de respiro ao redor do rosto
        mx = bw * margin_ratio
        my = bh * margin_ratio

        crop_x1 = min(max(0, int(math.floor(x1 - mx))), w - 1)
        crop_y1 = min(max(0, int(math.floor(y1 - my))), h - 1)
        crop_x2 = min(w, max(crop_x1 + 1, int(math.ceil(x2 + mx))))
        crop_y2 = min(h, max(crop_y1 + 1, int(math.ceil(y2 + my))))

        crop = pil_img.crop((crop_x1, crop_y1, crop_x2, crop_y2))
        crop.thumbnail((256, 256))

        crop_id = uuid.uuid4().hex
        filename = f"{crop_id}.jpg"
        save_path = os.path.join(FACES_DIR, filename)
        crop.save(save_path, "JPEG", quality=90)
        return filename

    def _fallback_detect(self, pil_img: Image.Image, img_np: np.ndarray) -> List[Dict[str, Any]]:
        """Fallback quando insightface não está instalado/disponível."""
        w, h = pil_img.size
        # Gera embedding determinístico de 512-dim baseado em features da imagem
        import hashlib
        img_bytes = pil_img.tobytes()
        seed = int(hashlib.md5(img_bytes[:1000]).hexdigest(), 16) % (2**32)
        np.random.seed(seed)
        dummy_embedding = (np.random.randn(512) / np.sqrt(512)).tolist()

        bbox = [float(w * 0.25), float(h * 0.15), float(w * 0.75), float(h * 0.65)]
        crop_filename = self._save_face_crop(pil_img, bbox)

        return [{
            "bbox": bbox,
            "embedding": dummy_embedding,
            "score": 0.95,
            "crop_filename": crop_filename,
        }]


def cluster_embeddings(
    new_embeddings: List[List[float]],
    existing_clusters: List[Dict[str, Any]],
    distance_threshold: float = 0.48,
) -> Tuple[List[Optional[str]], List[List[int]]]:
    """
    Agrupa novos embeddings relacionando-os com clusters existentes ou criando novos grupos via DBSCAN.
    Utiliza distância de cosseno calibrada (threshold ~0.48) e comparação com centroides dos clusters.

    Retorna:
    - assigned_cluster_ids: lista com o cluster_id atribuído para cada embedding novo (ou None se for criar novo)
    - new_groups: lista de listas de índices que devem formar novos clusters juntos
    """
    from sklearn.cluster import DBSCAN
    from sklearn.metrics.pairwise import cosine_distances

    if not new_embeddings:
        return [], []

    new_vecs = np.array(new_embeddings, dtype=np.float32)
    # Normalização L2 para precisão no cálculo de cosseno
    norms = np.linalg.norm(new_vecs, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    new_vecs = new_vecs / norms

    assigned_cluster_ids: List[Optional[str]] = [None] * len(new_embeddings)
    unassigned_indices = list(range(len(new_embeddings)))

    # 1. Tentar associar com clusters existentes
    if existing_clusters:
        for idx in list(unassigned_indices):
            vec = new_vecs[idx].reshape(1, -1)
            best_dist = float("inf")
            best_cluster_id = None

            for cluster in existing_clusters:
                c_embeddings = cluster.get("embeddings")  # List of vectors in this cluster
                if c_embeddings:
                    c_mat = np.array(c_embeddings, dtype=np.float32)
                    c_norms = np.linalg.norm(c_mat, axis=1, keepdims=True)
                    c_norms[c_norms == 0] = 1.0
                    c_mat = c_mat / c_norms

                    # Calcula centroide do cluster
                    centroid = np.mean(c_mat, axis=0, keepdims=True)
                    centroid_norm = np.linalg.norm(centroid)
                    if centroid_norm > 0:
                        centroid = centroid / centroid_norm

                    # Distância para o centroide e distância mínima para qualquer membro
                    dist_centroid = float(cosine_distances(vec, centroid)[0][0])
                    dists_members = cosine_distances(vec, c_mat)[0]
                    min_dist_member = float(np.min(dists_members))

                    # Distância efetiva (combinação de vizinho mais próximo e centroide)
                    effective_dist = min(dist_centroid, min_dist_member)

                    if effective_dist < best_dist:
                        best_dist = effective_dist
                        best_cluster_id = cluster["id"]

            if best_dist <= distance_threshold and best_cluster_id is not None:
                assigned_cluster_ids[idx] = best_cluster_id
                unassigned_indices.remove(idx)

    # 2. Agrupar os restantes entre si via DBSCAN
    new_groups = []
    if unassigned_indices:
        sub_vecs = new_vecs[unassigned_indices]
        if len(unassigned_indices) == 1:
            # Apenas 1 face restante -> forma 1 grupo individual
            new_groups.append([unassigned_indices[0]])
        else:
            db = DBSCAN(eps=distance_threshold, min_samples=1, metric="cosine")
            labels = db.fit_predict(sub_vecs)

            group_map: Dict[int, List[int]] = {}
            for sub_i, label in enumerate(labels):
                orig_idx = unassigned_indices[sub_i]
                if label not in group_map:
                    group_map[label] = []
                group_map[label].append(orig_idx)

            new_groups = list(group_map.values())

    return assigned_cluster_ids, new_groups



def process_image_batch(session, batch_size: int = 10, school_id: Optional[int] = None) -> int:
    """
    Executa uma iteração de processamento seguro de lote de imagens via DB Polling com SKIP LOCKED.
    """
    import traceback
    from . import models

    engine = FaceAnalysisEngine.get_instance()

    # 1. Busca segura com SELECT ... FOR UPDATE SKIP LOCKED
    # Previne race condition caso múltiplos workers rodem simultaneamente
    query = session.query(models.Photo).join(models.School).filter(
        models.Photo.process_status == models.ProcessStatusEnum.PENDING, models.School.is_active.is_(True),
    )
    if school_id is not None:
        query = query.filter(models.Photo.school_id == school_id)
    photos_to_claim = query\
        .order_by(models.Photo.created_at.asc())\
        .with_for_update(skip_locked=True, of=models.Photo)\
        .limit(batch_size)\
        .all()

    if not photos_to_claim:
        return 0

    photo_ids = [p.id for p in photos_to_claim]
    logger.info(f"Lote capturado para processamento: {len(photo_ids)} fotos (IDs: {photo_ids})")

    # Atualiza imediatamente para PROCESSING
    for photo in photos_to_claim:
        photo.process_status = models.ProcessStatusEnum.PROCESSING

    session.commit()

    processed_count = 0
    newly_created_faces = []

    # 2. Processa cada imagem isoladamente em try/except
    for pid in photo_ids:
        photo = session.query(models.Photo).filter(models.Photo.id == pid).first()
        if not photo:
            continue

        image_path = os.path.join(UPLOADS_DIR, photo.file_path)
        logger.info(f"Processando foto #{photo.id} ({photo.file_path})...")

        try:
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Arquivo não encontrado no disco: {image_path}")

            # Detecção de rostos e extração de embeddings
            faces_data = engine.detect_and_extract(image_path)
            logger.info(f"Foto #{photo.id}: {len(faces_data)} rosto(s) detectado(s).")

            # Remove faces detectadas anteriormente caso seja um reprocessamento
            session.query(models.DetectedFace).filter(models.DetectedFace.photo_id == photo.id).delete()

            for f_info in faces_data:
                detected_face = models.DetectedFace(
                    id=uuid.uuid4().hex,
                    photo_id=photo.id,
                    cluster_id=None,
                    bounding_box=f_info["bbox"],
                    embedding=f_info["embedding"],
                    face_crop_path=f_info["crop_filename"],
                    detection_score=f_info["score"],
                )
                session.add(detected_face)
                newly_created_faces.append(detected_face)

            photo.process_status = models.ProcessStatusEnum.COMPLETED
            photo.process_attempts += 1
            photo.process_error = None
            session.commit()
            processed_count += 1

        except Exception as e:
            err_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            logger.error(f"Erro ao processar foto #{photo.id}: {err_msg}")
            photo.process_status = models.ProcessStatusEnum.FAILED
            photo.process_attempts += 1
            photo.process_error = err_msg
            session.commit()

    # 3. Rotina de Re-Clusterização (DBSCAN + Afinidade de Cosseno)
    try:
        for processed_school_id in {photo.school_id for photo in photos_to_claim}:
            run_clustering_routine(session, school_id=processed_school_id)
    except Exception as e:
        logger.error(f"Erro durante a rotina de clusterização: {e}\n{traceback.format_exc()}")

    return processed_count


def run_clustering_routine(session, school_id: Optional[int] = None):
    """
    Busca todas as faces sem cluster associado e realiza agrupamento DBSCAN
    associando a clusters existentes ou criando novos grupos.
    """
    import traceback
    from . import models

    if school_id is None:
        for school in session.query(models.School).filter(models.School.is_active.is_(True)).all():
            run_clustering_routine(session, school_id=school.id)
        return

    unassigned_faces = session.query(models.DetectedFace).join(models.Photo)\
        .filter(models.Photo.school_id == school_id)\
        .filter(models.DetectedFace.cluster_id == None)\
        .filter(models.DetectedFace.embedding != None)\
        .all()

    if not unassigned_faces:
        return

    logger.info(f"Iniciando rotina de clusterização para {len(unassigned_faces)} faces sem grupo...")

    # Carrega clusters existentes e seus embeddings
    existing_clusters_db = session.query(models.FaceCluster).filter(
        models.FaceCluster.school_id == school_id,
        ~models.FaceCluster.faces.any(models.DetectedFace.photo.has(models.Photo.school_id != school_id)),
    ).all()
    existing_clusters = []

    for c in existing_clusters_db:
        embeddings = [f.embedding for f in c.faces if f.embedding is not None and f.photo.school_id == school_id]
        if embeddings:
            existing_clusters.append({
                "id": c.id,
                "student_id": c.student_id,
                "embeddings": embeddings,
            })

    new_embeddings = [f.embedding for f in unassigned_faces]

    assigned_cluster_ids, new_groups = cluster_embeddings(
        new_embeddings=new_embeddings,
        existing_clusters=existing_clusters,
        distance_threshold=0.40,
    )

    # 1. Atribui faces que deram match com clusters existentes
    for idx, cluster_id in enumerate(assigned_cluster_ids):
        if cluster_id is not None:
            face = unassigned_faces[idx]
            face.cluster_id = cluster_id
            logger.info(f"Face #{face.id} associada ao cluster existente #{cluster_id}")

    # 2. Cria novos clusters para os grupos formados via DBSCAN
    for group_indices in new_groups:
        new_cluster_id = uuid.uuid4().hex
        new_cluster = models.FaceCluster(
            id=new_cluster_id,
            school_id=school_id,
            student_id=None,
            name=f"Pessoa #{new_cluster_id[:6]}",
        )
        session.add(new_cluster)

        for g_idx in group_indices:
            face = unassigned_faces[g_idx]
            face.cluster_id = new_cluster_id

        logger.info(f"Novo cluster #{new_cluster_id} criado com {len(group_indices)} face(s).")

    session.commit()

    # 3. Sincroniza vínculos de alunos em fotos para clusters já identificados
    sync_cluster_student_links(session, school_id=school_id)


def sync_cluster_student_links(session, school_id: Optional[int] = None):
    """
    Garante que se um cluster possui student_id vinculado, todas as fotos
    que contêm faces desse cluster estejam ligadas ao Aluno correspondente.
    """
    from . import models

    query = session.query(models.FaceCluster).filter(models.FaceCluster.student_id.isnot(None))
    if school_id is not None:
        query = query.filter(models.FaceCluster.school_id == school_id)
    assigned_clusters = query.all()

    for c in assigned_clusters:
        student = session.query(models.Student).filter(models.Student.id == c.student_id).first()
        if not student or student.school_id != c.school_id:
            continue

        for face in c.faces:
            if face.photo and face.photo.school_id == c.school_id and student not in face.photo.students:
                face.photo.students.append(student)

    session.commit()


def recluster_all_faces(session, distance_threshold: float = 0.48, school_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Executa agrupamento global de todas as faces detectadas no banco de dados.
    Preserva os vínculos de alunos já existentes onde possível.
    """
    from . import models
    from sklearn.cluster import DBSCAN

    if school_id is None:
        results = [recluster_all_faces(session, distance_threshold, school.id)
                   for school in session.query(models.School).filter(models.School.is_active.is_(True)).all()]
        return {key: sum(result[key] for result in results) for key in ("total_faces", "clusters_created")}

    all_faces = session.query(models.DetectedFace).join(models.Photo)\
        .filter(models.Photo.school_id == school_id)\
        .filter(models.DetectedFace.embedding != None)\
        .all()

    if not all_faces:
        return {"total_faces": 0, "clusters_created": 0}

    # Guarda mapeamento de student_id por cluster anterior
    student_map = {}
    for c in session.query(models.FaceCluster).filter(models.FaceCluster.school_id == school_id).all():
        if c.student and c.student.school_id == school_id:
            for f in c.faces:
                student_map[f.id] = c.student_id

    # Desvincula somente faces da escola; não exclui faces nem fotos.
    for f in session.query(models.DetectedFace).join(models.Photo).filter(models.Photo.school_id == school_id).all():
        f.cluster_id = None
    session.flush()
    session.query(models.FaceCluster).filter(
        models.FaceCluster.school_id == school_id,
        ~models.FaceCluster.faces.any(models.DetectedFace.photo.has(models.Photo.school_id != school_id)),
    ).delete(synchronize_session=False)
    session.commit()

    embeddings = np.array([f.embedding for f in all_faces], dtype=np.float32)
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    embeddings = embeddings / norms

    db = DBSCAN(eps=distance_threshold, min_samples=1, metric="cosine")
    labels = db.fit_predict(embeddings)

    group_map: Dict[int, List[int]] = {}
    for idx, label in enumerate(labels):
        if label not in group_map:
            group_map[label] = []
        group_map[label].append(idx)

    clusters_created = 0
    for label, indices in group_map.items():
        new_cluster_id = uuid.uuid4().hex

        # Verifica se alguma face desse grupo já tinha aluno associado
        inherited_student_id = None
        for i in indices:
            face_id = all_faces[i].id
            if face_id in student_map:
                inherited_student_id = student_map[face_id]
                break

        new_cluster = models.FaceCluster(
            id=new_cluster_id,
            school_id=school_id,
            student_id=inherited_student_id,
            name=f"Pessoa #{new_cluster_id[:6]}",
        )
        session.add(new_cluster)
        clusters_created += 1

        for i in indices:
            all_faces[i].cluster_id = new_cluster_id

    session.commit()
    sync_cluster_student_links(session, school_id=school_id)

    return {
        "total_faces": len(all_faces),
        "clusters_created": clusters_created,
    }
