from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvSettings(BaseSettings):
    """
    Configurações exclusivas de ambiente (lidas do arquivo .env ou variáveis de ambiente).
    Apenas parâmetros de infraestrutura e segredos pertencem a este escopo.
    """
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parents[1] / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/prisma"
    SECRET_KEY: str = "uma-chave-secreta-muito-segura-para-desenvolvimento"


env_settings = EnvSettings()


class AppProperties:
    """
    Propriedades e regras fixas do sistema Prisma.
    Centralizadas exclusivamente aqui no código, sem duplicar no .env.
    """
    # Reconhecimento Facial & Agrupamento (InsightFace / DBSCAN / Agglomerative)
    FACE_DISTANCE_THRESHOLD: float = 0.58       # Distância de cosseno máxima (~0.42 similaridade ArcFace)
    FACE_MIN_DETECTION_SCORE: float = 0.52      # Confiança mínima de detecção para descartar ruídos/fundo
    FACE_MIN_SIZE_PX: int = 32                  # Tamanho mínimo da face (px) para processamento

    # Sugestões de Match Facial (Comparação e Pareamento para Confirmação Humana)
    MATCH_SUGGESTION_MAX_DISTANCE: float = 0.68     # Distância máxima de cosseno para sugerir match
    MATCH_SUGGESTION_MIN_SIMILARITY: float = 35.0   # Porcentagem mínima de similaridade (%)
    MATCH_SUGGESTION_DEFAULT_LIMIT: int = 15        # Quantidade limite padrão de sugestões retornadas


properties = AppProperties()


class Settings:
    """
    Fachada que consolida o acesso às configurações de ambiente e propriedades fixas da aplicação.
    """
    # Ambiente
    @property
    def DATABASE_URL(self) -> str:
        return env_settings.DATABASE_URL

    @property
    def SECRET_KEY(self) -> str:
        return env_settings.SECRET_KEY

    # Propriedades de negócio
    FACE_DISTANCE_THRESHOLD: float = properties.FACE_DISTANCE_THRESHOLD
    FACE_MIN_DETECTION_SCORE: float = properties.FACE_MIN_DETECTION_SCORE
    FACE_MIN_SIZE_PX: int = properties.FACE_MIN_SIZE_PX

    MATCH_SUGGESTION_MAX_DISTANCE: float = properties.MATCH_SUGGESTION_MAX_DISTANCE
    MATCH_SUGGESTION_MIN_SIMILARITY: float = properties.MATCH_SUGGESTION_MIN_SIMILARITY
    MATCH_SUGGESTION_DEFAULT_LIMIT: int = properties.MATCH_SUGGESTION_DEFAULT_LIMIT


settings = Settings()
