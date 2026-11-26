-- EcoParce: Políticas de Row-Level Security (RLS) de mínimo privilegio para PostgreSQL
-- Sin reglas abiertas (cero USING(true) / WITH CHECK(true)). Separadas por SELECT/INSERT/UPDATE/DELETE.
-- Inmutabilidad garantizada a nivel BD (UPDATE/DELETE denegados con false en auditoría y gateway).

ALTER TABLE "usuario" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "usuario" FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "rls_usuario_select" ON "usuario";
CREATE POLICY "rls_usuario_select" ON "usuario" FOR SELECT
    USING (current_setting('app.rls_bypass', true) = '1' OR current_setting('app.current_user_role', true) = 'SISTEMA' OR id::text = NULLIF(current_setting('app.current_user_id', true), ''));
DROP POLICY IF EXISTS "rls_usuario_insert" ON "usuario";
CREATE POLICY "rls_usuario_insert" ON "usuario" FOR INSERT
    WITH CHECK (current_setting('app.rls_bypass', true) = '1' OR current_setting('app.current_user_role', true) = 'SISTEMA');
DROP POLICY IF EXISTS "rls_usuario_update" ON "usuario";
CREATE POLICY "rls_usuario_update" ON "usuario" FOR UPDATE
    USING (current_setting('app.rls_bypass', true) = '1' OR current_setting('app.current_user_role', true) = 'SISTEMA' OR id::text = NULLIF(current_setting('app.current_user_id', true), ''))
    WITH CHECK (current_setting('app.rls_bypass', true) = '1' OR current_setting('app.current_user_role', true) = 'SISTEMA' OR id::text = NULLIF(current_setting('app.current_user_id', true), ''));
DROP POLICY IF EXISTS "rls_usuario_delete" ON "usuario";
CREATE POLICY "rls_usuario_delete" ON "usuario" FOR DELETE
    USING (current_setting('app.rls_bypass', true) = '1' OR current_setting('app.current_user_role', true) = 'SISTEMA' OR id::text = NULLIF(current_setting('app.current_user_id', true), ''));

ALTER TABLE "consentimiento" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "consentimiento" FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "rls_consentimiento_select" ON "consentimiento";
CREATE POLICY "rls_consentimiento_select" ON "consentimiento" FOR SELECT
    USING (current_setting('app.rls_bypass', true) = '1' OR current_setting('app.current_user_role', true) = 'SISTEMA' OR usuario_id::text = NULLIF(current_setting('app.current_user_id', true), ''));
DROP POLICY IF EXISTS "rls_consentimiento_insert" ON "consentimiento";
CREATE POLICY "rls_consentimiento_insert" ON "consentimiento" FOR INSERT
    WITH CHECK (current_setting('app.rls_bypass', true) = '1' OR current_setting('app.current_user_role', true) = 'SISTEMA' OR usuario_id::text = NULLIF(current_setting('app.current_user_id', true), ''));
DROP POLICY IF EXISTS "rls_consentimiento_update" ON "consentimiento";
CREATE POLICY "rls_consentimiento_update" ON "consentimiento" FOR UPDATE
    USING (current_setting('app.rls_bypass', true) = '1' OR current_setting('app.current_user_role', true) = 'SISTEMA' OR usuario_id::text = NULLIF(current_setting('app.current_user_id', true), ''))
    WITH CHECK (current_setting('app.rls_bypass', true) = '1' OR current_setting('app.current_user_role', true) = 'SISTEMA' OR usuario_id::text = NULLIF(current_setting('app.current_user_id', true), ''));
DROP POLICY IF EXISTS "rls_consentimiento_delete" ON "consentimiento";
CREATE POLICY "rls_consentimiento_delete" ON "consentimiento" FOR DELETE
    USING (current_setting('app.rls_bypass', true) = '1' OR current_setting('app.current_user_role', true) = 'SISTEMA' OR usuario_id::text = NULLIF(current_setting('app.current_user_id', true), ''));

ALTER TABLE "solicitud_admin" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "solicitud_admin" FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "rls_solicitud_select" ON "solicitud_admin";
CREATE POLICY "rls_solicitud_select" ON "solicitud_admin" FOR SELECT
    USING (current_setting('app.rls_bypass', true) = '1' OR current_setting('app.current_user_role', true) = 'SISTEMA' OR usuario_id::text = NULLIF(current_setting('app.current_user_id', true), ''));
DROP POLICY IF EXISTS "rls_solicitud_insert" ON "solicitud_admin";
CREATE POLICY "rls_solicitud_insert" ON "solicitud_admin" FOR INSERT
    WITH CHECK (current_setting('app.rls_bypass', true) = '1' OR usuario_id::text = NULLIF(current_setting('app.current_user_id', true), ''));
DROP POLICY IF EXISTS "rls_solicitud_update" ON "solicitud_admin";
CREATE POLICY "rls_solicitud_update" ON "solicitud_admin" FOR UPDATE
    USING (current_setting('app.rls_bypass', true) = '1' OR current_setting('app.current_user_role', true) = 'SISTEMA')
    WITH CHECK (current_setting('app.rls_bypass', true) = '1' OR current_setting('app.current_user_role', true) = 'SISTEMA');
DROP POLICY IF EXISTS "rls_solicitud_delete" ON "solicitud_admin";
CREATE POLICY "rls_solicitud_delete" ON "solicitud_admin" FOR DELETE
    USING (current_setting('app.rls_bypass', true) = '1' OR current_setting('app.current_user_role', true) = 'SISTEMA');

ALTER TABLE "partida_trivia" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "partida_trivia" FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "rls_trivia_select" ON "partida_trivia";
CREATE POLICY "rls_trivia_select" ON "partida_trivia" FOR SELECT
    USING (current_setting('app.rls_bypass', true) = '1' OR current_setting('app.current_user_role', true) IN ('SISTEMA', 'CONTENIDO') OR usuario_id IS NULL OR usuario_id::text = NULLIF(current_setting('app.current_user_id', true), ''));
DROP POLICY IF EXISTS "rls_trivia_insert" ON "partida_trivia";
CREATE POLICY "rls_trivia_insert" ON "partida_trivia" FOR INSERT
    WITH CHECK (current_setting('app.rls_bypass', true) = '1' OR usuario_id IS NULL OR usuario_id::text = NULLIF(current_setting('app.current_user_id', true), ''));
DROP POLICY IF EXISTS "rls_trivia_update" ON "partida_trivia";
CREATE POLICY "rls_trivia_update" ON "partida_trivia" FOR UPDATE
    USING (current_setting('app.rls_bypass', true) = '1' OR usuario_id IS NULL OR usuario_id::text = NULLIF(current_setting('app.current_user_id', true), ''))
    WITH CHECK (current_setting('app.rls_bypass', true) = '1' OR usuario_id IS NULL OR usuario_id::text = NULLIF(current_setting('app.current_user_id', true), ''));
DROP POLICY IF EXISTS "rls_trivia_delete" ON "partida_trivia";
CREATE POLICY "rls_trivia_delete" ON "partida_trivia" FOR DELETE
    USING (current_setting('app.rls_bypass', true) = '1' OR current_setting('app.current_user_role', true) = 'SISTEMA' OR usuario_id::text = NULLIF(current_setting('app.current_user_id', true), ''));

ALTER TABLE "sugerencia" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "sugerencia" FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "rls_sugerencia_select" ON "sugerencia";
CREATE POLICY "rls_sugerencia_select" ON "sugerencia" FOR SELECT
    USING (current_setting('app.rls_bypass', true) = '1' OR current_setting('app.current_user_role', true) IN ('SISTEMA', 'CONTENIDO') OR usuario_id::text = NULLIF(current_setting('app.current_user_id', true), ''));
DROP POLICY IF EXISTS "rls_sugerencia_insert" ON "sugerencia";
CREATE POLICY "rls_sugerencia_insert" ON "sugerencia" FOR INSERT
    WITH CHECK (current_setting('app.rls_bypass', true) = '1' OR usuario_id IS NULL OR usuario_id::text = NULLIF(current_setting('app.current_user_id', true), ''));
DROP POLICY IF EXISTS "rls_sugerencia_update" ON "sugerencia";
CREATE POLICY "rls_sugerencia_update" ON "sugerencia" FOR UPDATE
    USING (current_setting('app.rls_bypass', true) = '1' OR current_setting('app.current_user_role', true) IN ('SISTEMA', 'CONTENIDO'))
    WITH CHECK (current_setting('app.rls_bypass', true) = '1' OR current_setting('app.current_user_role', true) IN ('SISTEMA', 'CONTENIDO'));
DROP POLICY IF EXISTS "rls_sugerencia_delete" ON "sugerencia";
CREATE POLICY "rls_sugerencia_delete" ON "sugerencia" FOR DELETE
    USING (current_setting('app.rls_bypass', true) = '1' OR current_setting('app.current_user_role', true) = 'SISTEMA');

ALTER TABLE "registro_auditoria" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "registro_auditoria" FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "rls_auditoria_select" ON "registro_auditoria";
CREATE POLICY "rls_auditoria_select" ON "registro_auditoria" FOR SELECT
    USING (current_setting('app.rls_bypass', true) = '1' OR current_setting('app.current_user_role', true) = 'SISTEMA');
DROP POLICY IF EXISTS "rls_auditoria_insert" ON "registro_auditoria";
CREATE POLICY "rls_auditoria_insert" ON "registro_auditoria" FOR INSERT
    WITH CHECK (current_setting('app.rls_bypass', true) = '1' OR current_setting('app.current_user_role', true) IN ('VISITANTE', 'CONTENIDO', 'SISTEMA', 'API_GATEWAY'));
DROP POLICY IF EXISTS "rls_auditoria_no_update" ON "registro_auditoria";
CREATE POLICY "rls_auditoria_no_update" ON "registro_auditoria" FOR UPDATE
    USING (false)
    WITH CHECK (false);
DROP POLICY IF EXISTS "rls_auditoria_no_delete" ON "registro_auditoria";
CREATE POLICY "rls_auditoria_no_delete" ON "registro_auditoria" FOR DELETE
    USING (false);

ALTER TABLE "api_clave" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "api_clave" FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "rls_api_clave_select" ON "api_clave";
CREATE POLICY "rls_api_clave_select" ON "api_clave" FOR SELECT
    USING (current_setting('app.rls_bypass', true) = '1' OR current_setting('app.current_user_role', true) = 'SISTEMA' OR propietario_id::text = NULLIF(current_setting('app.current_user_id', true), ''));
DROP POLICY IF EXISTS "rls_api_clave_insert" ON "api_clave";
CREATE POLICY "rls_api_clave_insert" ON "api_clave" FOR INSERT
    WITH CHECK (current_setting('app.rls_bypass', true) = '1' OR current_setting('app.current_user_role', true) = 'SISTEMA');
DROP POLICY IF EXISTS "rls_api_clave_update" ON "api_clave";
CREATE POLICY "rls_api_clave_update" ON "api_clave" FOR UPDATE
    USING (current_setting('app.rls_bypass', true) = '1' OR current_setting('app.current_user_role', true) = 'SISTEMA')
    WITH CHECK (current_setting('app.rls_bypass', true) = '1' OR current_setting('app.current_user_role', true) = 'SISTEMA');
DROP POLICY IF EXISTS "rls_api_clave_delete" ON "api_clave";
CREATE POLICY "rls_api_clave_delete" ON "api_clave" FOR DELETE
    USING (current_setting('app.rls_bypass', true) = '1' OR current_setting('app.current_user_role', true) = 'SISTEMA');

ALTER TABLE "api_gateway_log" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "api_gateway_log" FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "rls_gw_log_select" ON "api_gateway_log";
CREATE POLICY "rls_gw_log_select" ON "api_gateway_log" FOR SELECT
    USING (current_setting('app.rls_bypass', true) = '1' OR current_setting('app.current_user_role', true) = 'SISTEMA');
DROP POLICY IF EXISTS "rls_gw_log_insert" ON "api_gateway_log";
CREATE POLICY "rls_gw_log_insert" ON "api_gateway_log" FOR INSERT
    WITH CHECK (current_setting('app.rls_bypass', true) = '1' OR current_setting('app.current_user_role', true) IN ('VISITANTE', 'CONTENIDO', 'SISTEMA', 'API_GATEWAY'));
DROP POLICY IF EXISTS "rls_gw_log_no_update" ON "api_gateway_log";
CREATE POLICY "rls_gw_log_no_update" ON "api_gateway_log" FOR UPDATE
    USING (false)
    WITH CHECK (false);
DROP POLICY IF EXISTS "rls_gw_log_no_delete" ON "api_gateway_log";
CREATE POLICY "rls_gw_log_no_delete" ON "api_gateway_log" FOR DELETE
    USING (false);
