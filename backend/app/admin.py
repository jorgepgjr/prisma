from sqladmin import Admin, ModelView
from fastapi import FastAPI
from .db import engine
from .models import User, Class, Student, Photo, Tag

class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.name, User.email, User.role, User.created_at]
    column_searchable_list = [User.name, User.email]
    column_sortable_list = [User.id, User.name, User.created_at]
    form_columns = [User.name, User.email, User.hashed_password, User.role]
    name = "Usuário"
    name_plural = "Usuários"
    icon = "fa-solid fa-user"

class ClassAdmin(ModelView, model=Class):
    column_list = [Class.id, Class.name, Class.year, Class.created_at]
    column_searchable_list = [Class.name]
    column_sortable_list = [Class.id, Class.name, Class.year]
    form_columns = [Class.name, Class.year]
    name = "Turma"
    name_plural = "Turmas"
    icon = "fa-solid fa-graduation-cap"

class StudentAdmin(ModelView, model=Student):
    column_list = [Student.id, Student.name, Student.class_id, Student.status, Student.marketing_allowed]
    column_searchable_list = [Student.name]
    column_sortable_list = [Student.id, Student.name, Student.status]
    form_columns = [Student.name, Student.class_id, Student.status, Student.marketing_allowed]
    name = "Estudante"
    name_plural = "Estudantes"
    icon = "fa-solid fa-child"

class PhotoAdmin(ModelView, model=Photo):
    column_list = [Photo.id, Photo.file_path, Photo.title, Photo.uploaded_by_user_id, Photo.class_id, Photo.status, Photo.created_at]
    column_searchable_list = [Photo.title, Photo.file_path]
    column_sortable_list = [Photo.id, Photo.status, Photo.created_at]
    form_columns = [Photo.file_path, Photo.title, Photo.description, Photo.uploaded_by_user_id, Photo.class_id, Photo.status]
    name = "Foto"
    name_plural = "Fotos"
    icon = "fa-solid fa-image"

class TagAdmin(ModelView, model=Tag):
    column_list = [Tag.id, Tag.name, Tag.created_at]
    column_searchable_list = [Tag.name]
    column_sortable_list = [Tag.id, Tag.name, Tag.created_at]
    form_columns = [Tag.name]
    name = "Tag"
    name_plural = "Tags"
    icon = "fa-solid fa-tag"

def setup_admin(app: FastAPI):
    # Cria o painel administrativo no endpoint /admin
    admin = Admin(app, engine, title="Portal Escolar - Administração")
    admin.add_view(UserAdmin)
    admin.add_view(ClassAdmin)
    admin.add_view(StudentAdmin)
    admin.add_view(PhotoAdmin)
    admin.add_view(TagAdmin)
