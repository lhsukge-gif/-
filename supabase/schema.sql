-- Run once in the Supabase project's SQL Editor. Safe to run again.
begin;
create table if not exists public.gallery_works (
  id text primary key,
  payload jsonb not null check (jsonb_typeof(payload) = 'object' and payload->>'id' = id)
);
alter table public.gallery_works enable row level security;
revoke all on public.gallery_works from anon, authenticated;
grant select, insert, update, delete on public.gallery_works to service_role;

-- Lock the affected row so simultaneous reactions/comments cannot overwrite each other.
create or replace function public.gallery_update(work_id text, action text, input_data jsonb)
returns boolean language plpgsql security invoker set search_path = public as $$
declare
  doc jsonb;
  reaction_key text;
begin
  select payload into doc from public.gallery_works where id = work_id for update;
  if not found then return false; end if;
  if action = 'react' then
    if input_data->>'emoji' not in ('👍', '💗', '😮', '💡') or coalesce(input_data->>'client','') = '' then
      raise exception 'Invalid reaction';
    end if;
    reaction_key := (input_data->>'client') || ':' || (input_data->>'emoji');
    if (doc->'reactions') ? reaction_key then
      doc := jsonb_set(doc, '{reactions}', (doc->'reactions') - reaction_key);
    else
      doc := jsonb_set(doc, '{reactions}', (doc->'reactions') || jsonb_build_object(reaction_key, input_data->>'emoji'));
    end if;
  elsif action = 'comments' then
    if coalesce(input_data->>'name','') = '' or coalesce(input_data->>'text','') = '' then
      raise exception 'Invalid comment';
    end if;
    doc := jsonb_set(doc, '{comments}', (doc->'comments') || jsonb_build_array(input_data));
  else
    raise exception 'Invalid action';
  end if;
  update public.gallery_works set payload = doc where id = work_id;
  return true;
end;
$$;
revoke all on function public.gallery_update(text,text,jsonb) from public, anon, authenticated;
grant execute on function public.gallery_update(text,text,jsonb) to service_role;

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('gallery-posters', 'gallery-posters', true, 4194304,
        array['image/png','image/jpeg','image/webp','image/gif'])
on conflict (id) do nothing;
-- Public reading of posters is intentional. Uploads are server-only, through the secret key.
commit;
