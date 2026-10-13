package mid

import (
	"archive/tar"
	"archive/zip"
	"bytes"
	"compress/gzip"
	"fmt"
	"io"
	"path"
	"strings"
	"unicode/utf8"
)

const (
	fsPackTokenPrefix = "fsp_"
)

// Is_BuiltinFsPack - встроенное дерево, без скачивания с центра.
func Is_BuiltinFsPack(value string) bool {
	pack := strings.TrimSpace(value)
	return pack == "" || pack == "ubuntu-22.04" || pack == "builtin"
}

// Is_PackToken - токен пакета с центра (fsp_...).
func Is_PackToken(value string) bool {
	return strings.HasPrefix(strings.TrimSpace(value), fsPackTokenPrefix)
}

type ExpandedFsPack struct {
	Tree   map[string]string
	Dirs   map[string]struct{}
	Binary map[string]struct{}
}

// Expand_Archive разворачивает zip или tar.gz в дерево fake shell.
func Expand_Archive(raw []byte) (*ExpandedFsPack, error) {
	if len(raw) == 0 {
		return nil, fmt.Errorf("пустой архив fs pack")
	}
	if is_Zip(raw) {
		return expand_Zip(raw)
	}
	if is_Gzip(raw) {
		return expand_TarGz(raw)
	}
	return nil, fmt.Errorf("нужен zip или tar.gz")
}

func is_Zip(raw []byte) bool {
	return len(raw) >= 4 && raw[0] == 'P' && raw[1] == 'K'
}

func is_Gzip(raw []byte) bool {
	return len(raw) >= 2 && raw[0] == 0x1f && raw[1] == 0x8b
}

func normalize_ArchivePath(raw string) (string, bool) {
	cleaned := strings.ReplaceAll(raw, "\\", "/")
	cleaned = strings.TrimSpace(cleaned)
	if cleaned == "" || strings.HasSuffix(cleaned, "/") {
		// Каталог обработаем отдельно
		dir := path.Clean("/" + strings.Trim(cleaned, "/"))
		if dir == "." || dir == "/" {
			return "/", true
		}
		if strings.Contains(dir, "..") {
			return "", false
		}
		return dir, true
	}
	full := path.Clean("/" + strings.TrimPrefix(cleaned, "/"))
	if full == "." || strings.Contains(full, "..") {
		return "", false
	}
	if !strings.HasPrefix(full, "/") {
		full = "/" + full
	}
	return full, true
}

func add_ParentDirs(dirs map[string]struct{}, full string) {
	dirs["/"] = struct{}{}
	dir := full
	for {
		slash := strings.LastIndex(dir, "/")
		if slash <= 0 {
			break
		}
		dir = dir[:slash]
		if dir == "" {
			break
		}
		dirs[dir] = struct{}{}
	}
}

func is_BinaryContent(data []byte) bool {
	if bytes.IndexByte(data, 0) >= 0 {
		return true
	}
	return !utf8.Valid(data)
}

func expand_Zip(raw []byte) (*ExpandedFsPack, error) {
	reader, err := zip.NewReader(bytes.NewReader(raw), int64(len(raw)))
	if err != nil {
		return nil, err
	}
	out := &ExpandedFsPack{
		Tree:   map[string]string{},
		Dirs:   map[string]struct{}{"/": {}},
		Binary: map[string]struct{}{},
	}
	for _, file := range reader.File {
		name := file.Name
		if file.FileInfo().IsDir() || strings.HasSuffix(name, "/") {
			full, ok := normalize_ArchivePath(name)
			if !ok {
				continue
			}
			out.Dirs[full] = struct{}{}
			add_ParentDirs(out.Dirs, full)
			continue
		}
		full, ok := normalize_ArchivePath(name)
		if !ok || full == "/" {
			continue
		}
		rc, err := file.Open()
		if err != nil {
			continue
		}
		data, err := io.ReadAll(rc)
		_ = rc.Close()
		if err != nil {
			continue
		}
		add_ParentDirs(out.Dirs, full)
		if is_BinaryContent(data) {
			out.Binary[full] = struct{}{}
			continue
		}
		out.Tree[full] = string(data)
	}
	return out, nil
}

func expand_TarGz(raw []byte) (*ExpandedFsPack, error) {
	gz, err := gzip.NewReader(bytes.NewReader(raw))
	if err != nil {
		return nil, err
	}
	defer gz.Close()
	tr := tar.NewReader(gz)
	out := &ExpandedFsPack{
		Tree:   map[string]string{},
		Dirs:   map[string]struct{}{"/": {}},
		Binary: map[string]struct{}{},
	}
	for {
		hdr, err := tr.Next()
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, err
		}
		name := hdr.Name
		switch hdr.Typeflag {
		case tar.TypeDir:
			full, ok := normalize_ArchivePath(name)
			if !ok {
				continue
			}
			out.Dirs[full] = struct{}{}
			add_ParentDirs(out.Dirs, full)
		case tar.TypeReg, tar.TypeRegA:
			full, ok := normalize_ArchivePath(name)
			if !ok || full == "/" {
				continue
			}
			data, err := io.ReadAll(tr)
			if err != nil {
				continue
			}
			add_ParentDirs(out.Dirs, full)
			if is_BinaryContent(data) {
				out.Binary[full] = struct{}{}
				continue
			}
			out.Tree[full] = string(data)
		default:
			continue
		}
	}
	return out, nil
}
