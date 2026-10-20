import asyncio
import json
import os
import unittest
from datetime import timedelta

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi import FastAPI, HTTPException
from app import db, models, schemas, security
from app.mobile_auth import router, login, me, MobileLogin
from app.dependencies import get_current_user
from app.admin_api import create_user, update_user
from app.families import create_parent, update_parent, create_family_profile
from app.account_email import ensure_available_email


class MobileAuthTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if db.engine.dialect.name != "sqlite" or db.engine.url.database != ":memory:":
            raise RuntimeError("Testes permitidos somente no SQLite em memória.")
        models.Base.metadata.create_all(db.engine)
        cls.password = security.get_password_hash("secret1")

    @classmethod
    def tearDownClass(cls):
        models.Base.metadata.drop_all(db.engine)

    def setUp(self):
        self.session = db.SessionLocal()
        self.school = models.School(name="Escola teste")
        self.session.add(self.school)
        self.session.flush()
        self.teacher = models.User(name="Professora", email="teacher@test.com", school_id=self.school.id,
                                   role=models.RoleEnum.PROFESSOR, hashed_password=self.password)
        self.coordinator = models.User(name="Coordenação", email="coord@test.com", school_id=self.school.id,
                                       role=models.RoleEnum.COORDENADOR, hashed_password=self.password)
        self.marketing = models.User(name="Marketing", email="marketing@test.com", school_id=self.school.id,
                                    role=models.RoleEnum.MARKETING, hashed_password=self.password)
        self.parent = models.Parent(id="parent-uuid",name="Familiar",email="family@test.com",school_id=self.school.id,
                                    hashed_password=self.password,is_active=True)
        self.session.add_all([self.teacher,self.coordinator,self.marketing,self.parent])
        self.session.commit()
        self.app=FastAPI()
        self.app.include_router(router,prefix="/api/mobile/auth")
        self.app.dependency_overrides[db.get_db]=lambda:self.session

    def tearDown(self):
        self.session.close()
        models.Base.metadata.drop_all(db.engine)
        models.Base.metadata.create_all(db.engine)

    def request(self,path,body=None,token=None):
        sent=[]
        headers=[(b"content-type",b"application/json")]
        if token: headers.append((b"authorization",f"Bearer {token}".encode()))
        scope={"type":"http","asgi":{"version":"3.0"},"http_version":"1.1","method":"POST" if body is not None else "GET",
               "scheme":"http","path":path,"raw_path":path.encode(),"query_string":b"","root_path":"",
               "headers":headers,"server":("test",80),"client":("test",123)}
        async def receive(): return {"type":"http.request","body":json.dumps(body).encode(),"more_body":False}
        async def send(message): sent.append(message)
        asyncio.run(self.app(scope,receive,send))
        status=next(item["status"] for item in sent if item["type"]=="http.response.start")
        content=b"".join(item.get("body",b"") for item in sent if item["type"]=="http.response.body")
        return status,json.loads(content)

    def logged(self,email):
        return login(MobileLogin(email=email,password="secret1"),self.session)

    def test_http_login_returns_server_profile_and_normalizes_email(self):
        status,data=self.request("/api/mobile/auth/login",{"email":" TEACHER@test.com ","password":"secret1","profile":"FAMILIAR","school_id":999})
        self.assertEqual(status,200)
        self.assertEqual(data["account"]["profile"],"PROFESSOR")
        self.assertEqual(data["account"]["school_id"],self.school.id)
        status,context=self.request("/api/mobile/auth/me",token=data["access_token"])
        self.assertEqual(status,200)
        self.assertEqual(context,data["account"])

    def test_tokens_remain_compatible_and_cannot_cross_account_types(self):
        teacher=self.logged(self.teacher.email)
        parent=self.logged(self.parent.email)
        self.assertEqual(get_current_user(teacher.access_token,self.session).id,self.teacher.id)
        self.assertEqual(security.get_current_parent(parent.access_token,self.session).id,self.parent.id)
        for function,token in [(get_current_user,parent.access_token),(security.get_current_parent,teacher.access_token)]:
            with self.assertRaises(HTTPException) as error: function(token,self.session)
            self.assertEqual(error.exception.status_code,401)

    def test_family_without_students_can_login(self):
        result=self.logged(self.parent.email)
        self.assertEqual(result.account.profile,"FAMILIAR")
        self.assertEqual(self.parent.children,[])
        self.assertEqual(me(result.access_token,self.session).id,self.parent.id)

    def test_coordinator_marketing_and_invalid_password_are_refused(self):
        for email,status in [(self.coordinator.email,403),(self.marketing.email,403),("unknown@test.com",401)]:
            actual,_=self.request("/api/mobile/auth/login",{"email":email,"password":"secret1"})
            self.assertEqual(actual,status)
        actual,_=self.request("/api/mobile/auth/login",{"email":self.teacher.email,"password":"wrong"})
        self.assertEqual(actual,401)
        actual,_=self.request("/api/mobile/auth/login",{"email":self.teacher.email,"password":"é"*80})
        self.assertEqual(actual,401)

    def test_inactive_accounts_school_and_changed_role_invalidate_session(self):
        for account in [self.teacher,self.parent]:
            token=self.logged(account.email).access_token
            account.is_active=False
            self.session.commit()
            self.assertEqual(self.request("/api/mobile/auth/me",token=token)[0],403)
            account.is_active=True
            self.session.commit()
        token=self.logged(self.teacher.email).access_token
        self.school.is_active=False
        self.session.commit()
        self.assertEqual(self.request("/api/mobile/auth/me",token=token)[0],403)
        self.school.is_active=True
        self.teacher.role=models.RoleEnum.COORDENADOR
        self.session.commit()
        self.assertEqual(self.request("/api/mobile/auth/me",token=token)[0],403)

    def test_expired_forged_legacy_and_missing_tokens_are_refused(self):
        tokens=[None,"invalid",security.create_access_token({"sub":self.teacher.email}),
                security.create_access_token({"sub":self.teacher.email,"mobile_profile":"FAMILIAR"}),
                security.create_access_token({"sub":self.teacher.email,"mobile_profile":"PROFESSOR"},expires_delta=timedelta(seconds=-1))]
        for token in tokens: self.assertEqual(self.request("/api/mobile/auth/me",token=token)[0],401)

    def test_legacy_duplicate_is_reported_without_changing_records(self):
        self.parent.email=" TEACHER@TEST.COM "
        self.session.commit()
        for path,body in [("/api/mobile/auth/login",{"email":self.teacher.email,"password":"secret1"})]:
            self.assertEqual(self.request(path,body)[0],409)
        self.assertEqual(self.session.query(models.User).count(),3)
        self.assertEqual(self.session.query(models.Parent).count(),1)

    def test_cross_profile_email_creation_and_updates_are_blocked(self):
        actions=[
            lambda:create_user(schemas.UserCreate(name="Novo",email="FAMILY@test.com",password="secret1",role="PROFESSOR"),self.coordinator,self.session),
            lambda:create_parent(schemas.FamilyParentCreate(name="Familiar novo",email="TEACHER@test.com",password="secret1"),self.coordinator,self.session),
            lambda:update_user(self.teacher.id,schemas.UserUpdate(email="FAMILY@test.com"),self.coordinator,self.session),
            lambda:update_parent(self.parent.id,schemas.FamilyParentUpdate(email="TEACHER@test.com"),self.coordinator,self.session),
        ]
        for action in actions:
            with self.assertRaises(HTTPException) as error: action()
            self.assertEqual(error.exception.status_code,409)
        self.assertEqual(ensure_available_email(self.session," TEACHER@TEST.COM ",user_id=self.teacher.id),self.teacher.email)

    def test_inline_family_creation_also_checks_professional_email(self):
        classroom=models.Class(school_id=self.school.id,name="Turma",year=2026)
        self.session.add(classroom);self.session.flush()
        student=models.Student(school_id=self.school.id,class_id=classroom.id,name="Aluno")
        self.session.add(student);self.session.commit()
        with self.assertRaises(HTTPException) as error:
            create_family_profile(student.id,schemas.FamilyAccountCreate(parent_name="Familiar",parent_email=self.teacher.email,initial_password="secret1"),self.coordinator,self.session)
        self.assertEqual(error.exception.status_code,409)
        self.assertIsNone(student.child_profile)
