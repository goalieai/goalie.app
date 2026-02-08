CREATE TABLE IF NOT EXISTS google_tokens (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
      google_email TEXT NOT NULL,
      access_token TEXT NOT NULL,
      refresh_token TEXT NOT NULL,
      token_uri TEXT DEFAULT 'https://oauth2.googleapis.com/token',
      scopes TEXT[] DEFAULT ARRAY['https://www.googleapis.com/auth/calendar'],
      expiry TIMESTAMPTZ,
      created_at TIMESTAMPTZ DEFAULT NOW(),
      updated_at TIMESTAMPTZ DEFAULT NOW(),
      UNIQUE(user_id, google_email)
  );

ALTER TABLE google_tokens ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can disconnect own calendar" ON google_tokens FOR DELETE USING (auth.uid () = user_id);

CREATE POLICY "Users can view own connection metadata" ON google_tokens FOR
SELECT USING (auth.uid () = user_id);

CREATE TRIGGER google_tokens_updated_at
      BEFORE UPDATE ON google_tokens
      FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE POLICY "Backend can insert tokens" ON google_tokens FOR
INSERT
WITH
    CHECK (true);

CREATE POLICY "Backend can update tokens" ON google_tokens FOR
UPDATE USING (true)
WITH
    CHECK (true);